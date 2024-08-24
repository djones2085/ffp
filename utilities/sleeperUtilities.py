import requests
import pandas as pd

# Global Constants
POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']
LEAGUE_SIZE = 12

TEAM_ROSTER_NEEDS = {
    'Team1': ['RB', 'WR'],
    'Team2': ['QB', 'TE'],
    'MyTeam': ['RB', 'WR', 'TE'],
}

DRAFTED_PLAYERS = {
    'MyTeam': [],
    'Team1': [],
    'Team2': [],
}

# File path to the Excel file
file_path = '/Users/danieljones/dev/ffp/utilities/cbs_ff_projection_data.xlsx'

# Load and process the Excel file
# TODO: Handle defense and special teams data ingestion
def load_and_process_excel(file_path):
    excel_data = pd.ExcelFile(file_path)
    cbs_data = pd.concat([pd.read_excel(file_path, sheet_name=sheet) for sheet in excel_data.sheet_names])

    def process_player_data(player):
        if isinstance(player, str):
            parts = player.split()
            if len(parts) >= 4:
                first_name = parts[0]
                last_name = parts[1]
                search_full_name = f"{first_name.lower()}{last_name.lower()}"
                return search_full_name
        return pd.NA

    # Apply the function to process player data and add only the search_full_name column
    cbs_data['search_full_name'] = cbs_data['PLAYER'].apply(process_player_data)
    
    # Ensure FPTS is present and correctly processed
    if 'FPTS' not in cbs_data.columns:
        raise ValueError("FPTS column not found in the Excel file.")
    
    # Drop the 'PLAYER' column after processing
    cbs_data = cbs_data.drop(columns=['PLAYER'])
    
    return cbs_data

# Fetch projections from Sleeper and return as a DataFrame
def fetch_data_from_sleeper():
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        # Create a list to store player data
        sleeper_data = []
        for player_id, player_info in data.items():
            if 'fantasy_positions' in player_info and player_info['fantasy_positions']:
                positions = player_info['fantasy_positions']
                if any(pos in POSITIONS for pos in positions):
                    sleeper_data.append({
                        'player_id': player_id,
                        'search_full_name': player_info.get('search_full_name', '').lower(),
                        'full_name': player_info.get('full_name', 'Unknown'),
                        'position': positions[0],
                        'team': player_info.get('team', '')
                    })
        
        # Convert the list to a DataFrame
        sleeper_df = pd.DataFrame(sleeper_data)
        return sleeper_df
    else:
        raise Exception(f"Failed to fetch data from Sleeper API: {response.status_code}")

# Merge Excel data with Sleeper data
def merge_data(cbs_data, sleeper_data):
    # Merge the Excel data with the Sleeper data on 'search_full_name'
    merged_data = pd.merge(cbs_data, sleeper_data, on='search_full_name', how='left', suffixes=('', '_sleeper'))
    
    # Ensure FPTS column is retained correctly
    if 'FPTS' not in merged_data.columns:
        raise ValueError("FPTS column is missing after merging data.")
    
    return merged_data

# Identify baseline players using the DataFrame directly
def identify_baseline_players(merged_data_df):
    baseline_players_points = {}
    
    for position in POSITIONS:
        players_in_position = merged_data_df[merged_data_df['position'] == position]
        players_in_position = players_in_position.sort_values(by='FPTS', ascending=False)
        
        if not players_in_position.empty:
            baseline_index = min(LEAGUE_SIZE - 1, len(players_in_position) - 1)
            baseline_players_points[position] = float(players_in_position.iloc[baseline_index]['FPTS'])
        else:
            baseline_players_points[position] = 0.0  # Ensure the default is a standard float

    return baseline_players_points

# Calculate VORP using the DataFrame directly
def calculate_vorp(df, baseline_players):
    df['VORP'] = df.apply(lambda row: row['FPTS'] - baseline_players.get(row['position'], 0), axis=1)
    vorp_scores = df.set_index('search_full_name')['VORP'].to_dict()
    return vorp_scores

# Filter by team needs
def filter_by_team_needs(vorp_scores, sleeper_data):
    team_filtered_players = {}
    
    for team, needs in TEAM_ROSTER_NEEDS.items():
        team_filtered_players[team] = {
            player_id: vorp_scores[player_id] 
            for player_id in vorp_scores 
            if sleeper_data[sleeper_data['player_id'] == player_id]['position'].values[0] in needs
        }
    
    return team_filtered_players

# Simulate draft for all teams
def simulate_draft_for_all_teams(vorp_scores, sleeper_data, filtered_team_vorp_scores, df):
    simulated_draft_results = {}
    
    for team, filtered_scores in filtered_team_vorp_scores.items():
        team_needs = TEAM_ROSTER_NEEDS[team]
        if team in DRAFTED_PLAYERS:
            current_team = DRAFTED_PLAYERS[team].copy()
        else:
            current_team = []

        max_total_points = 0
        best_pick = None

        for player_id, vorp in filtered_scores.items():
            if player_id not in current_team:
                simulated_team = current_team.copy()
                simulated_team.append(player_id)

                for position in team_needs:
                    if position not in sleeper_data[sleeper_data['player_id'].isin(simulated_team)]['position'].tolist():
                        remaining_players = {
                            p: v for p, v in vorp_scores.items() 
                            if sleeper_data[sleeper_data['player_id'] == p]['position'].values[0] == position
                        }
                        best_remaining = max(remaining_players, key=remaining_players.get)
                        simulated_team.append(best_remaining)

                # Calculate total points using the FPTS values from df
                total_points = sum([df.loc[df['player_id'] == p, 'FPTS'].values[0] for p in simulated_team])
                if total_points > max_total_points:
                    max_total_points = total_points
                    best_pick = player_id

        simulated_draft_results[team] = {
            'best_pick': best_pick,
            'total_points': max_total_points
        }

    return simulated_draft_results

# Choose the best pick
def choose_best_pick(simulated_draft_results):
    my_team_results = simulated_draft_results['MyTeam']
    best_pick = my_team_results['best_pick']
    best_total_points = my_team_results['total_points']
    
    return best_pick, best_total_points

# Main function
def main():
    try:
        # Load and process the Excel file
        cbs_data = load_and_process_excel(file_path)
        print("Excel data loaded and processed successfully!")
        # # Print the first few rows of the DataFrame
        # print(cbs_data.head())
    except Exception as e:
        print(f"Error loading or processing Excel data: {e}")
        return

    try:
        sleeper_data = fetch_data_from_sleeper()
        print("Sleeper data fetched successfully!")
        # # Print the first few rows of the DataFrame
        # print(sleeper_data.head())
    except Exception as e:
        print(f"Error fetching projections: {e}")
        return
    
    try:
        merged_data = merge_data(cbs_data, sleeper_data)
        print("Data merged successfully!")
        # # Print the first few rows of the DataFrame
        # print(merged_data.head())
    except Exception as e:
        print(f"Error merging data: {e}")
        return

    try:
        baseline_players = identify_baseline_players(merged_data)
        # Print the baseline players
        print(baseline_players)
        vorp_scores = calculate_vorp(merged_data, baseline_players)
        print("VORP Scores calculated successfully!")
    except Exception as e:
        print(f"Error calculating VORP scores: {e}")
        return

    try:
        filtered_team_vorp_scores = filter_by_team_needs(vorp_scores, sleeper_data)
        print("Filtered VORP Scores by Team Needs:")
    except Exception as e:
        print(f"Error filtering by team needs: {e}")
        return

    try:
        simulated_draft_results = simulate_draft_for_all_teams(vorp_scores, sleeper_data, filtered_team_vorp_scores, merged_data)
        print("Simulated Draft Results:")
    except Exception as e:
        print(f"Error simulating draft: {e}")
        return

    try:
        best_pick, best_points = choose_best_pick(simulated_draft_results)
        print(f"Best pick: {best_pick} with projected points: {best_points}")
    except Exception as e:
        print(f"Error choosing best pick: {e}")

if __name__ == "__main__":
    main()
