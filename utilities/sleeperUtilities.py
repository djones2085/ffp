import requests
import pandas as pd
import re
from fuzzywuzzy import fuzz

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
file_path = '/Users/danieljones/dev/ffp/utilities/cbs_ff_projection_data.xlsx'

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
                return pd.Series([search_full_name, None])
        elif pd.notna(row.get('TEAM')):  # Process as a defense/special team
            team_name = row['TEAM']
            # Map the CBS team name to the Sleeper team abbreviation
            for player_id, cbs_team in TEAM_NAME_MAPPING.items():
                if cbs_team == team_name:
                    mapped_team_name = player_id.upper()  # Keep team names in uppercase
                    return pd.Series([None, mapped_team_name])
        return pd.Series([pd.NA, pd.NA])

    # Apply the function to process each row and add the relevant identifier columns
    cbs_data[['search_full_name', 'search_team_name']] = cbs_data.apply(process_row, axis=1)
    
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

from fuzzywuzzy import fuzz

def merge_data(cbs_data, sleeper_data):
    # Normalize names in the CBS data
    cbs_data['full_name'] = cbs_data['search_full_name'].apply(lambda x: normalize_name(x) if pd.notna(x) else x)
    
    # Normalize names in the Sleeper data
    sleeper_data['full_name'] = sleeper_data['full_name'].apply(lambda x: normalize_name(x) if pd.notna(x) else x)

    # Standardize team names to uppercase
    cbs_data['search_team_name'] = cbs_data['search_team_name'].str.upper()
    sleeper_data['team'] = sleeper_data['team'].str.upper()

    # Merge on full names
    player_merge = pd.merge(cbs_data[cbs_data['full_name'].notna()], sleeper_data,
                            left_on='full_name', right_on='full_name',
                            how='left', suffixes=('', '_sleeper'))

    # Check for unmatched rows in player_merge
    unmatched_players = player_merge[player_merge['player_id'].isna()]
    
    # Log unmatched players and continue
    if not unmatched_players.empty:
        print(f"{len(unmatched_players)} unmatched players found. Logging and continuing...")
        for _, row in unmatched_players.iterrows():
            print(f"Unmatched player: {row['full_name']}")
            # Optional: Add fuzzy matching here
            closest_match = None
            max_ratio = 0
            for _, sleeper_row in sleeper_data.iterrows():
                ratio = fuzz.ratio(row['full_name'], sleeper_row['full_name'])
                if ratio > max_ratio:
                    max_ratio = ratio
                    closest_match = sleeper_row['full_name']
            
            if max_ratio > 85:  # Consider it a match if similarity is above 85%
                print(f"Closest match for {row['full_name']} is {closest_match} with a similarity of {max_ratio}%")
                # Optionally handle the matched player, e.g., manually update the player ID
            else:
                print(f"No close match found for {row['full_name']}.")
        # Remove unmatched rows or handle as needed
        player_merge = player_merge[player_merge['player_id'].notna()]

    # Merge on team defenses using 'team' for rows where position is 'DEF'
    def_merge = pd.merge(cbs_data[cbs_data['search_team_name'].notna()], sleeper_data[sleeper_data['position'] == 'DEF'],
                         left_on='search_team_name', right_on='team',
                         how='left', suffixes=('', '_team'))

    # Check for unmatched rows in def_merge
    unmatched_defs = def_merge[def_merge['player_id'].isna()]
    
    # Log unmatched defenses and continue
    if not unmatched_defs.empty:
        print(f"{len(unmatched_defs)} unmatched defenses found. Logging and continuing...")
        for _, row in unmatched_defs.iterrows():
            print(f"Unmatched defense for team: {row['search_team_name']}")
        # Remove unmatched rows or handle as needed
        def_merge = def_merge[def_merge['player_id'].notna()]

    # Concatenate both merged DataFrames
    combined_merge = pd.concat([player_merge, def_merge], ignore_index=True)

    # Ensure that we have a single FPTS column
    if 'FPTS' not in combined_merge.columns:
        raise ValueError("FPTS column is missing after merging data.")

    # Clean up any unnecessary columns
    columns_to_drop = ['search_full_name', 'search_team_name', 'player_id_team', 'full_name_team', 'position_team', 'team_team']
    existing_columns_to_drop = [col for col in columns_to_drop if col in combined_merge.columns]

    final_result = combined_merge.drop(columns=existing_columns_to_drop)

    return final_result



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
    vorp_scores = df.set_index('search_full_name')['VORP'].to_dict()
    return vorp_scores

def filter_by_team_needs(vorp_scores, sleeper_data, cbs_data):
    team_filtered_players = {}

    for team, needs in TEAM_ROSTER_NEEDS.items():
        print(f"Processing team: {team} with needs: {needs}")  # Debugging statement
        team_filtered_players[team] = {}

        for player_id in vorp_scores:
            # Safeguard to check if player_id exists in sleeper_data
            player_info = sleeper_data[sleeper_data['player_id'] == player_id]
            if player_info.empty:
                # Additional debugging: Print the player ID and the corresponding search_full_name in cbs_data
                matching_cbs = cbs_data[cbs_data['search_full_name'] == player_id]
                if not matching_cbs.empty:
                    print(f"Mismatch found for player ID {player_id}. Possible mismatch with Sleeper data:")
                    print(matching_cbs[['search_full_name', 'TEAM']])
                else:
                    print(f"No matching player found for player ID {player_id} in CBS data.")
                continue  # Skip this iteration if no matching player is found

            # Extract position of the player and check if it matches the team's needs
            player_position = player_info['position'].values[0]
            print(f"Player ID {player_id} - Position: {player_position}")  # Debugging statement
            if player_position in needs:
                team_filtered_players[team][player_id] = vorp_scores[player_id]
                print(f"Added player_id {player_id} to team {team}")  # Debugging statement

        # Warning if no players were found that match the team's needs
        if not team_filtered_players[team]:
            print(f"Warning: No players found for team {team} based on needs {needs}")

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
        cbs_data = load_and_process_excel(file_path)
        print("Excel data loaded and processed successfully!")
    except Exception as e:
        print(f"Error loading or processing Excel data: {e}")
        return

    try:
        sleeper_data = fetch_data_from_sleeper()
        print("Sleeper data fetched successfully!")
    except Exception as e:
        print(f"Error fetching Sleeper data: {e}")
        return

    print("CBS Data:")
    print(cbs_data.head(10))
    print("Sleeper Data:")
    print(sleeper_data.head(10))

    try:
        merged_data = merge_data(cbs_data, sleeper_data)
        if merged_data is None:
            print("Process stopped due to unmatched players or defenses.")
            return
        print("Data merged successfully!")
    except Exception as e:
        print(f"Error merging data: {e}")
        return

if __name__ == "__main__":
    main()
