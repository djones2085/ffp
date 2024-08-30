import requests
import pandas as pd
import re
# from fuzzywuzzy import fuzz

# Global Constants
POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']
LEAGUE_SIZE = 10

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

TEAM_NAME_MAPPING = {
    'HOU': 'Houston',
    'NE': 'New England',
    'BAL': 'Baltimore',
    'PIT': 'Pittsburgh',
    'IND': 'Indianapolis',
    'ARI': 'Arizona',
    'SEA': 'Seattle',
    'LV': 'Las Vegas',
    'NYJ': 'N.Y. Jets',
    'DAL': 'Dallas',
    'WAS': 'Washington',
    'LAC': 'L.A. Chargers',
    'TB': 'Tampa Bay',
    'CLE': 'Cleveland',
    'ATL': 'Atlanta',
    'CAR': 'Carolina',
    'JAX': 'Jacksonville',
    'LAR': 'L.A. Rams',
    'NO': 'New Orleans',
    'GB': 'Green Bay',
    'MIA': 'Miami',
    'DET': 'Detroit',
    'BUF': 'Buffalo',
    'PHI': 'Philadelphia',
    'SF': 'San Francisco',
    'NYG': 'N.Y. Giants',
    'TEN': 'Tennessee',
    'CHI': 'Chicago',
    'CIN': 'Cincinnati',
    'DEN': 'Denver',
    'KC': 'Kansas City',
    'MIN': 'Minnesota'
}

# File path to the Excel file
excel_file_path = '/Users/danieljones/dev/ffp/utilities/cbs_ff_projection_data.xlsx'

def normalize_name(name):
    # Remove special characters and spaces, convert to lowercase
    return re.sub(r'[^a-z0-9]', '', name.lower())

# Load and process the Excel file
def load_and_process_excel(file_path):
    excel_data = pd.ExcelFile(file_path)
    cbs_data = pd.concat([pd.read_excel(file_path, sheet_name=sheet) for sheet in excel_data.sheet_names])

    def process_row(row):
        if pd.notna(row.get('PLAYER')):  # Process as a player
            parts = row['PLAYER'].split()
            if len(parts) >= 2:  # At least first and last name
                first_name = parts[0]
                last_name = parts[1]
                search_full_name = f"{first_name.lower()}{last_name.lower()}"
                # Generate the full_name with proper capitalization
                full_name = f"{first_name.capitalize()} {last_name.capitalize()}"
                return pd.Series([search_full_name, None, full_name])
        elif pd.notna(row.get('TEAM')):  # Process as a defense/special team
            team_name = row['TEAM']
            # Map the CBS team name to the Sleeper team abbreviation
            for player_id, cbs_team in TEAM_NAME_MAPPING.items():
                if cbs_team == team_name:
                    mapped_team_name = player_id.upper()  # Keep team names in uppercase
                    return pd.Series([None, mapped_team_name, None])
        return pd.Series([pd.NA, pd.NA, pd.NA])

    # Apply the function to process each row and add the relevant identifier columns
    cbs_data[['search_full_name', 'search_team_name', 'full_name']] = cbs_data.apply(process_row, axis=1)
    
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
                    # Safely handle None values before calling .lower() and convert team names to uppercase
                    search_full_name = player_info.get('search_full_name', '')
                    full_name = player_info.get('full_name', 'Unknown')
                    team = player_info.get('team', '').upper() if player_info.get('team') else ''
                    
                    sleeper_data.append({
                        'player_id': player_id if 'DEF' in positions else player_id.lower(),  # Keep DEF IDs as uppercase (team abbreviations)
                        'search_full_name': search_full_name.lower() if search_full_name else '',
                        'full_name': full_name,
                        'position': positions[0],
                        'team': team  # Convert to uppercase for consistency
                    })
        
        # Convert the list to a DataFrame
        sleeper_df = pd.DataFrame(sleeper_data)
        return sleeper_df
    else:
        raise Exception(f"Failed to fetch data from Sleeper API: {response.status_code}")

def merge_data(cbs_data, sleeper_data):
    # Merge on `full_name` directly, applying the suffix '_cbs' only to columns from cbs_data in case of a name conflict
    player_merge = pd.merge(cbs_data[cbs_data['full_name'].notna()], sleeper_data,
                            left_on='full_name', right_on='full_name',
                            how='left', suffixes=('_cbs', ''))

    # Drop unmatched rows in player_merge if needed
    player_merge = player_merge.dropna(subset=['player_id'])

    # Merge on team defenses using 'team' for rows where position is 'DEF'
    def_merge = pd.merge(cbs_data[cbs_data['search_team_name'].notna()], sleeper_data[sleeper_data['position'] == 'DEF'],
                         left_on='search_team_name', right_on='team',
                         how='left', suffixes=('_cbs', ''))

    # Drop unmatched rows in def_merge if needed
    def_merge = def_merge.dropna(subset=['player_id'])

    # Concatenate both merged DataFrames
    combined_merge = pd.concat([player_merge, def_merge], ignore_index=True)

    # Ensure that we have a single FPTS column
    if 'FPTS' not in combined_merge.columns:
        raise ValueError("FPTS column is missing after merging data.")

    # Return the final DataFrame without dropping any columns
    return combined_merge

# Filter by team needs
def filter_by_team_needs(vorp_scores, sleeper_data):
    team_filtered_players = {}
    
    for team, needs in TEAM_ROSTER_NEEDS.items():
        team_filtered_players[team] = {
            player_id: vorp_scores[player_id]
            for player_id in vorp_scores
            if sleeper_data[sleeper_data['player_id'] == player_id]['position'].values[0] in needs
        }

        if not team_filtered_players[team]:  # Check if filtering resulted in an empty dictionary
            print(f"Warning: No players found for team {team} based on needs {needs}")

    return team_filtered_players

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
    
    # Create a dictionary with player_id as the key and VORP as the value
    vorp_scores = df.set_index('player_id')['VORP'].to_dict()
    
    return vorp_scores

def filter_by_team_needs(vorp_scores, merged_data):
    team_filtered_players = {}

    for team, needs in TEAM_ROSTER_NEEDS.items():
        team_filtered_players[team] = {}

        for player_id, vorp in vorp_scores.items():
            # Retrieve the player's information from merged_data using player_id
            player_info = merged_data[merged_data['player_id'] == player_id]
            
            # Safeguard: Check if the player exists in merged_data
            if player_info.empty:
                continue  # Skip if the player is not found in merged_data

            # Extract the player's position
            player_position = player_info['position'].values[0]
            
            # Check if the player's position matches the team's needs
            if player_position in needs:
                team_filtered_players[team][player_id] = vorp

        # Warning if no players were found that match the team's needs
        if not team_filtered_players[team]:
            print(f"Warning: No players found for team {team} based on needs {needs}")

    return team_filtered_players

# Simulate draft for all teams
def simulate_draft_for_all_teams(vorp_scores, filtered_team_vorp_scores, merged_data):
    simulated_draft_results = {}
    
    for team, filtered_scores in filtered_team_vorp_scores.items():
        team_needs = TEAM_ROSTER_NEEDS[team]
        if team in DRAFTED_PLAYERS:
            current_team = DRAFTED_PLAYERS[team].copy()
        else:
            current_team = []

        max_total_points = 0.0
        best_pick = None

        for player_id, vorp in filtered_scores.items():
            if player_id not in current_team:
                simulated_team = current_team.copy()
                simulated_team.append(player_id)

                for position in team_needs:
                    # Check if the position is already filled by a player in the simulated team
                    team_positions = merged_data[merged_data['player_id'].isin(simulated_team)]['position'].tolist()
                    if position not in team_positions:
                        remaining_players = {
                            p: v for p, v in vorp_scores.items() 
                            if merged_data.loc[merged_data['player_id'] == p, 'position'].values[0] == position
                        }
                        if remaining_players:
                            best_remaining = max(remaining_players, key=remaining_players.get)
                            simulated_team.append(best_remaining)

                # Calculate total points using the FPTS values from merged_data
                total_points = sum([merged_data.loc[merged_data['player_id'] == p, 'FPTS'].values[0] for p in simulated_team])
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

def inspect_player(cbs_data, sleeper_data, full_name):
    print(f"Inspecting player: {full_name}")

    # Normalize the full name for comparison
    normalized_name = normalize_name(full_name)

    # Inspect in CBS data
    cbs_player_data = cbs_data[cbs_data['full_name'] == normalized_name]
    print("\nCBS Data for the player:")
    if not cbs_player_data.empty:
        print(cbs_player_data)
    else:
        print("Player not found in CBS data.")

    # Inspect in Sleeper data
    sleeper_player_data = sleeper_data[sleeper_data['full_name'] == normalized_name]
    print("\nSleeper Data for the player:")
    if not sleeper_player_data.empty:
        print(sleeper_player_data)
    else:
        print("Player not found in Sleeper data.")

    # Attempt additional checks for common discrepancies
    print("\nAttempting alternative checks...")

    # Try partial matches or alternative normalization approaches
    alternative_cbs_data = cbs_data[cbs_data['full_name'].str.contains(normalized_name[:5], na=False)]
    alternative_sleeper_data = sleeper_data[sleeper_data['full_name'].str.contains(normalized_name[:5], na=False)]
    
    if not alternative_cbs_data.empty:
        print("\nPossible matches in CBS Data:")
        print(alternative_cbs_data)
    
    if not alternative_sleeper_data.empty:
        print("\nPossible matches in Sleeper Data:")
        print(alternative_sleeper_data)

def main():
    try:
        # Load and process the Excel file
        cbs_data = load_and_process_excel(excel_file_path)
        # # Export cbs data to a csv file for inspection
        # cbs_data.to_csv('cbs_data.csv', index=False)
    except Exception as e:
        print(f"Error loading or processing Excel data: {e}")
        return

    try:
        sleeper_data = fetch_data_from_sleeper()
        # # Export sleeper data to a csv file for inspection
        # sleeper_data.to_csv('sleeper_data.csv', index=False)
    except Exception as e:
        print(f"Error fetching Sleeper data: {e}")
        return

    try:
        merged_data = merge_data(cbs_data, sleeper_data)
        # # Export merged data to a csv file for inspection
        # merged_data.to_csv('merged_data.csv', index=False)
        if merged_data is None:
            print("Process stopped due to unmatched players or defenses.")
            return
    except Exception as e:
        print(f"Error during data merging: {e}")
        return

    # Identify baseline players
    try:
        baseline_players = identify_baseline_players(merged_data)
        # # Print baseline players dictionary for inspection
        # print(baseline_players)
    except Exception as e:
        print(f"Error identifying baseline players: {e}")
        return

    # Calculate VORP
    try:
        vorp_scores = calculate_vorp(merged_data, baseline_players)
        # # Print vorp_scores for inspection
        # print(vorp_scores)
    except Exception as e:
        print(f"Error calculating VORP scores: {e}")
        return

    # Filter by team needs
    try:
        filtered_team_vorp_scores = filter_by_team_needs(vorp_scores, merged_data)
        # # Print filtered_team_vorp_scores for inspection
        # print(filtered_team_vorp_scores)
    except Exception as e:
        print(f"Error filtering players by team needs: {e}")
        return

    # Simulate the draft for all teams
    try:
        simulated_draft_results = simulate_draft_for_all_teams(vorp_scores, filtered_team_vorp_scores, merged_data)
        # # Print simulated_draft_results for inspection
        # print(simulated_draft_results)
    except Exception as e:
        print(f"Error during draft simulation: {e}")
        return
    
    # Choose the best pick for your team
    try:
        best_pick, best_total_points = choose_best_pick(simulated_draft_results)
        
        # Look up the full_name of the best pick using merged_data
        best_pick_name = merged_data.loc[merged_data['player_id'] == best_pick, 'full_name'].values[0]
        
        print(f"The best pick for your team is {best_pick_name} with a projected total points of {best_total_points}.")
    except Exception as e:
        print(f"Error choosing the best pick: {e}")
        return

if __name__ == "__main__":
    main()
