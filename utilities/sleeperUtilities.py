import requests
import pandas as pd
import re

# Global Constants
LEAGUE_ID = '1120130617145937920'
MY_USER_NAME = 'megaman2000'
MY_USER_ID = '1004174905258176512'
LEAGUE_SIZE = 12

# Updated POSITIONS list with clearer roles for FLEX and BENCH spots
POSITIONS = [
    'QB',        # 1 QB
    'RB', 'RB',  # 2 RB
    'WR', 'WR',  # 2 WR
    'TE',        # 1 TE
    'K',         # 1 K
    'DEF',       # 1 DEF
    'FLEX1', 'FLEX2',  # 2 FLEX (RB, WR, or TE)
    'BENCH1', 'BENCH2', 'BENCH3', 'BENCH4', 'BENCH5'  # 5 BENCH spots
]

# Placeholder for the team data
TEAMS = []
TEAM_ROSTER_NEEDS = {}
DRAFTED_PLAYERS = {}

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

def load_and_process_excel(file_path):
    excel_data = pd.ExcelFile(file_path)
    cbs_data = pd.concat([pd.read_excel(file_path, sheet_name=sheet) for sheet in excel_data.sheet_names])

    def process_row(row):
        if pd.notna(row.get('PLAYER')):  # Process as a player
            parts = row['PLAYER'].split()
            if len(parts) >= 4:  # Expecting 'First Name Last Name Position Team'
                first_name = parts[0]
                last_name = parts[1]
                position = parts[2]
                team = parts[3]
                search_full_name = f"{first_name.lower()}{last_name.lower()}"
                full_name = f"{first_name.capitalize()} {last_name.capitalize()}"
                return pd.Series([search_full_name, None, full_name, position, team])
        elif pd.notna(row.get('TEAM')):  # Process as a defense/special team
            team_name = row['TEAM']
            # Map the CBS team name to the Sleeper team abbreviation
            for player_id, cbs_team in TEAM_NAME_MAPPING.items():
                if cbs_team == team_name:
                    mapped_team_name = player_id.upper()  # Keep team names in uppercase
                    return pd.Series([None, mapped_team_name, None, 'DEF', None])
        return pd.Series([pd.NA, pd.NA, pd.NA, 'Unknown', pd.NA])

    # Apply the function to process each row and add the relevant identifier columns
    cbs_data[['search_full_name', 'search_team_name', 'full_name', 'position', 'team']] = cbs_data.apply(process_row, axis=1)
    
    # Ensure FPTS is present and correctly processed
    if 'FPTS' not in cbs_data.columns:
        raise ValueError("FPTS column not found in the Excel file.")
    
    # Drop the 'PLAYER' column after processing
    cbs_data = cbs_data.drop(columns=['PLAYER'])
    
    # Debug: Print the columns of the processed CBS data
    print("CBS Data Columns:", cbs_data.columns)
    
    return cbs_data

def fetch_data_from_sleeper():
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        sleeper_data = []
        for player_id, player_info in data.items():
            if 'fantasy_positions' in player_info and player_info['fantasy_positions']:
                positions = player_info['fantasy_positions']
                if any(pos in POSITIONS for pos in positions):
                    search_full_name = player_info.get('search_full_name', f"{player_info.get('first_name', '')}{player_info.get('last_name', '')}".lower())
                    full_name = player_info.get('full_name', 'Unknown')
                    team = player_info.get('team', '').upper() if player_info.get('team') else ''
                    
                    sleeper_data.append({
                        'player_id': player_id if 'DEF' in positions else player_id.lower(),  # Keep DEF IDs as uppercase (team abbreviations)
                        'search_full_name': search_full_name.lower() if search_full_name else '',
                        'full_name': full_name,
                        'position': positions[0],
                        'team': team  # Convert to uppercase for consistency
                    })
        
        sleeper_df = pd.DataFrame(sleeper_data)
        
        # Debug: Print the columns of the Sleeper data
        print("Sleeper Data Columns:", sleeper_df.columns)
        
        return sleeper_df
    else:
        raise Exception(f"Failed to fetch data from Sleeper API: {response.status_code}")

def merge_data(cbs_data, sleeper_data):
    # First, ensure that Sleeper data contains only unique player IDs
    sleeper_data_unique = sleeper_data.drop_duplicates(subset=['player_id'])

    # Merge the CBS data with the unique Sleeper data based on `search_full_name`
    player_merge = pd.merge(
        sleeper_data_unique, 
        cbs_data, 
        left_on='search_full_name', 
        right_on='search_full_name', 
        how='left', 
        suffixes=('', '_cbs')
    )

    # Merge on team defenses using 'team' for rows where position is 'DEF', keeping Sleeper data as the base
    def_merge = pd.merge(
        sleeper_data_unique[sleeper_data_unique['position'] == 'DEF'], 
        cbs_data[cbs_data['position'] == 'DEF'],
        left_on='team', 
        right_on='team', 
        how='left', 
        suffixes=('', '_cbs')
    )

    # Concatenate both merged DataFrames
    combined_merge = pd.concat([player_merge, def_merge], ignore_index=True)

    # Drop unnecessary duplicated columns if any remain
    combined_merge = combined_merge.drop(columns=['search_team_name', 'team_cbs'], errors='ignore')

    # Debug: Print the final combined columns and a preview of the data
    print("Combined Data Columns:", combined_merge.columns)
    print("Combined Data Preview:\n", combined_merge.head())

    # Return the final DataFrame without dropping any columns
    return combined_merge

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

def identify_baseline_players(merged_data_df):
    baseline_players_points = {}

    # Calculate position requirements dynamically from the POSITIONS list
    position_requirements = {}
    for position in POSITIONS:
        if position.startswith('BENCH') or position.startswith('FLEX'):
            continue  # Skip FLEX and BENCH for baseline calculations
        if position in position_requirements:
            position_requirements[position] += 1
        else:
            position_requirements[position] = 1

    for position, required_count in position_requirements.items():
        if position == 'FLEX1' or position == 'FLEX2':
            # FLEX can be RB, WR, or TE, so combine all those positions
            players_in_position = merged_data_df[
                merged_data_df['position'].isin(['RB', 'WR', 'TE'])
            ]
        else:
            players_in_position = merged_data_df[
                merged_data_df['position'] == position
            ]
        
        players_in_position = players_in_position.sort_values(by='FPTS', ascending=False)
        
        if not players_in_position.empty:
            # Calculate baseline index accounting for multiple players per position
            baseline_index = min((LEAGUE_SIZE * required_count) - 1, len(players_in_position) - 1)
            baseline_players_points[position] = float(players_in_position.iloc[baseline_index]['FPTS'])
        else:
            baseline_players_points[position] = 0.0  # Ensure the default is a standard float

    return baseline_players_points

def calculate_vorp(df, baseline_players):
    df['VORP'] = df.apply(lambda row: row['FPTS'] - baseline_players.get(row['position'], 0), axis=1)
    
    # Create a dictionary with player_id as the key and VORP as the value
    vorp_scores = df.set_index('player_id')['VORP'].to_dict()
    
    return vorp_scores

def simulate_draft_for_my_team(vorp_scores, team_needs, merged_data, my_team):
    print(f"Starting draft simulation for team: {my_team}")
    print(f"Initial available players count: {len(vorp_scores)}")
    print(f"Team needs for {my_team}: {team_needs[my_team]}")

    simulated_draft_results = {team: DRAFTED_PLAYERS.get(team, []).copy() for team in TEAM_ROSTER_NEEDS.keys()}
    available_players = set(merged_data['player_id']) - set(player for players in DRAFTED_PLAYERS.values() for player in players)

    if not available_players:
        print("No available players to draft.")
        return None, 0

    total_roster_needs = {
        team: {
            'QB': 2, 'RB': 2, 'WR': 2, 'TE': 1, 'K': 2, 'DEF': 2, 'FLEX1': 1, 'FLEX2': 1, 'BENCH1': 1, 'BENCH2': 1, 'BENCH3': 1, 'BENCH4': 1, 'BENCH5': 1
        } for team in TEAM_ROSTER_NEEDS.keys()
    }

    for team, drafted_players in simulated_draft_results.items():
        for player_id in drafted_players:
            player_info = merged_data.loc[merged_data['player_id'] == player_id]
            if player_info.empty:
                print(f"Warning: No position found for player ID {player_id}")
                continue
            
            position = player_info['position'].values[0]
            if total_roster_needs[team][position] > 0:
                total_roster_needs[team][position] -= 1
            elif position in ['RB', 'WR', 'TE'] and total_roster_needs[team]['FLEX1'] > 0:
                total_roster_needs[team]['FLEX1'] -= 1
            elif position in ['RB', 'WR', 'TE'] and total_roster_needs[team]['FLEX2'] > 0:
                total_roster_needs[team]['FLEX2'] -= 1
            else:
                for bench_spot in ['BENCH1', 'BENCH2', 'BENCH3', 'BENCH4', 'BENCH5']:
                    if total_roster_needs[team][bench_spot] > 0:
                        total_roster_needs[team][bench_spot] -= 1
                        break

    print(f"Total roster needs after adjusting for drafted players: {total_roster_needs}")

    best_final_pick = None
    max_total_points = float('-inf')
    best_simulated_team = None

    potential_picks = {
        player_id: vorp for player_id, vorp in vorp_scores.items()
        if player_id in available_players and vorp >= 0
        and (
            (merged_data.loc[merged_data['player_id'] == player_id, 'position'].values[0] in team_needs[my_team] or
            (merged_data.loc[merged_data['player_id'] == player_id, 'position'].values[0] in ['RB', 'WR', 'TE'] and team_needs[my_team]['FLEX1'] > 0)) or
            team_needs[my_team]['BENCH1'] > 0
        )
    }

    print(f"Potential picks for {my_team}: {potential_picks}")

    if not potential_picks:
        print(f"No valid picks available for {my_team} based on current needs.")
        return None, 0

    for player_id, vorp in potential_picks.items():
        simulated_draft_results_copy = {team: picks.copy() for team, picks in simulated_draft_results.items()}
        available_players_copy = available_players.copy()
        team_needs_copy = {team: needs.copy() for team, needs in total_roster_needs.items()}

        simulated_draft_results_copy[my_team].append(player_id)
        available_players_copy.remove(player_id)

        player_info = merged_data.loc[merged_data['player_id'] == player_id]
        if player_info.empty:
            print(f"Warning: No player data found for player ID {player_id}. Skipping.")
            continue
        
        player_position = player_info['position'].values[0]
        if team_needs_copy[my_team][player_position] > 0:
            team_needs_copy[my_team][player_position] -= 1
        elif player_position in ['RB', 'WR', 'TE'] and team_needs_copy[my_team]['FLEX1'] > 0:
            team_needs_copy[my_team]['FLEX1'] -= 1
        elif player_position in ['RB', 'WR', 'TE'] and team_needs_copy[my_team]['FLEX2'] > 0:
            team_needs_copy[my_team]['FLEX2'] -= 1
        else:
            for bench_spot in ['BENCH1', 'BENCH2', 'BENCH3', 'BENCH4', 'BENCH5']:
                if team_needs_copy[my_team][bench_spot] > 0:
                    team_needs_copy[my_team][bench_spot] -= 1
                    break

        simulate_remaining_draft(vorp_scores, team_needs_copy, merged_data, simulated_draft_results_copy, available_players_copy)

        try:
            total_points = sum(
                merged_data.loc[merged_data['player_id'] == p, 'FPTS'].values[0] for p in simulated_draft_results_copy[my_team]
            )
            print(f"Total points for simulated pick {player_id}: {total_points}")
        except IndexError:
            print(f"Error calculating points for player ID {player_id}. Player data might be missing.")
            continue

        if total_points > max_total_points:
            max_total_points = total_points
            best_final_pick = player_id
            best_simulated_team = simulated_draft_results_copy[my_team]

    if best_simulated_team:
        print(f"\nBest simulated team for {my_team} after picking {merged_data.loc[merged_data['player_id'] == best_final_pick, 'full_name'].values[0]}:")
        print(merged_data[merged_data['player_id'].isin(best_simulated_team)][['full_name', 'position', 'FPTS', 'VORP']])

    return best_final_pick, max_total_points

def simulate_remaining_draft(vorp_scores, team_needs, merged_data, draft_results, available_players):
    while any(sum(needs.values()) > 0 for needs in team_needs.values()):
        for team, needs in team_needs.items():
            if sum(needs.values()) == 0:
                continue

            best_pick = None
            max_vorp = float('-inf')

            for player_id in available_players:
                player_position = merged_data.loc[merged_data['player_id'] == player_id, 'position'].values[0]

                # Enforce the limit of 2 QBs, 2 Ks, and 2 DEFs
                if (player_position in ['QB', 'K', 'DEF'] and needs[player_position] <= 0):
                    continue

                if team_needs[team][player_position] > 0:
                    if vorp_scores[player_id] > max_vorp:
                        max_vorp = vorp_scores[player_id]
                        best_pick = player_id
                elif player_position in ['RB', 'WR', 'TE'] and needs['FLEX1'] > 0:
                    if vorp_scores[player_id] > max_vorp:
                        max_vorp = vorp_scores[player_id]
                        best_pick = player_id
                elif player_position in ['RB', 'WR', 'TE'] and needs['FLEX2'] > 0:
                    if vorp_scores[player_id] > max_vorp:
                        max_vorp = vorp_scores[player_id]
                        best_pick = player_id
                elif any(needs[bench_spot] > 0 for bench_spot in ['BENCH1', 'BENCH2', 'BENCH3', 'BENCH4', 'BENCH5']):
                    if vorp_scores[player_id] > max_vorp:
                        max_vorp = vorp_scores[player_id]
                        best_pick = player_id

            if best_pick:
                draft_results[team].append(best_pick)
                available_players.remove(best_pick)

                if player_position in needs:
                    needs[player_position] -= 1
                elif player_position in ['RB', 'WR', 'TE'] and needs['FLEX1'] > 0:
                    needs['FLEX1'] -= 1
                elif player_position in ['RB', 'WR', 'TE'] and needs['FLEX2'] > 0:
                    needs['FLEX2'] -= 1
                else:
                    for bench_spot in ['BENCH1', 'BENCH2', 'BENCH3', 'BENCH4', 'BENCH5']:
                        if needs[bench_spot] > 0:
                            needs[bench_spot] -= 1
                            break

    # Print the simulated team for each team after the draft is complete
    for team, players in draft_results.items():
        team_roster = merged_data[merged_data['player_id'].isin(players)]
        print(f"\nSimulated team for {team}:")
        print(team_roster[['full_name', 'position', 'FPTS', 'VORP']])

    return draft_results

def get_user_info(identifier):
    """
    Fetch the user object from Sleeper API using either username or user_id.

    Args:
        identifier (str): The Sleeper username or user ID.

    Returns:
        dict: A dictionary containing user information, including user_id.
    """
    url = f"https://api.sleeper.app/v1/user/{identifier}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            user_info = response.json()
            user_id = user_info.get("user_id")
            # print(f"User ID: {user_id}")
            return user_info
        else:
            print(f"Failed to retrieve user info: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_all_leagues_for_user(user_id, sport='nfl', season='2024'):
    """
    Fetch all leagues for a specific user in a given sport and season from the Sleeper API.

    Args:
        user_id (str): The numerical ID of the user.
        sport (str): The sport for the leagues (default is 'nfl').
        season (str): The season year (e.g., '2018', '2023').

    Returns:
        list: A list of dictionaries, each representing a league the user is in.
    """
    url = f"https://api.sleeper.app/v1/user/{user_id}/leagues/{sport}/{season}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to retrieve leagues: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
    
def get_rosters_for_league(league_id):
    """
    Fetch all rosters (teams) for a specific league from the Sleeper API.

    Args:
        league_id (str): The ID of the league.

    Returns:
        list: A list of dictionaries, each representing a roster (team) in the league.
    """
    url = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to retrieve rosters: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def fetch_league_rosters(league_id):
    """
    Fetch the roster information for a given league from the Sleeper API.
    
    Args:
        league_id (str): The league ID to fetch the rosters for.
    
    Returns:
        list: A list of dictionaries containing roster information for each team in the league.
    """
    url = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to retrieve rosters: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def update_teams_data(rosters):
    """
    Update the global TEAMS, TEAM_ROSTER_NEEDS, and DRAFTED_PLAYERS variables based on the fetched rosters.
    
    Args:
        rosters (list): A list of dictionaries containing roster information for each team.
    """
    global TEAMS, TEAM_ROSTER_NEEDS, DRAFTED_PLAYERS
    
    # Extract team names based on the owner's ID
    TEAMS = [f"Team_{roster['roster_id']}" for roster in rosters]
    
    # Update the TEAM_ROSTER_NEEDS and DRAFTED_PLAYERS dictionaries
    TEAM_ROSTER_NEEDS = {team: POSITIONS.copy() for team in TEAMS}
    DRAFTED_PLAYERS = {team: roster['players'] if roster['players'] else [] for team, roster in zip(TEAMS, rosters)}

def update_team_roster_needs(team, player_position, team_needs):
    """
    Update the roster needs for a given team after drafting a player.
    
    Args:
        team (str): The team name.
        player_position (str): The position of the drafted player.
        team_needs (dict): The current needs of all teams.
    """
    if team not in team_needs:
        print(f"Warning: Team '{team}' not found in TEAM_ROSTER_NEEDS.")
        return
    
    if player_position in team_needs[team]:
        team_needs[team].remove(player_position)
    elif player_position in ['RB', 'WR', 'TE'] and 'FLEX1' in team_needs[team]:
        team_needs[team].remove('FLEX1')
    elif player_position in ['RB', 'WR', 'TE'] and 'FLEX2' in team_needs[team]:
        team_needs[team].remove('FLEX2')
    elif 'BENCH1' in team_needs[team]:
        for i in range(1, 6):  # Attempt to remove from BENCH1 to BENCH5
            bench_spot = f'BENCH{i}'
            if bench_spot in team_needs[team]:
                team_needs[team].remove(bench_spot)
                break

def get_league_users(league_id):
    """
    Retrieves all users in a Sleeper league.

    Args:
        league_id (str): The ID of the league to retrieve users from.

    Returns:
        list: A list of dictionaries, each containing user information.
    """
    url = f"https://api.sleeper.app/v1/league/{league_id}/users"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        users = response.json()
        return users
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def main():
    # Step 1: Fetch league users and populate TEAMS
    print("Fetching league users...")
    users = get_league_users(LEAGUE_ID)
    
    if not users:
        print("No users found for the league.")
        return
    
    TEAMS = []
    for user in users:
        team_name = user['metadata'].get('team_name', 'Unnamed Team')
        user_id = user['user_id']
        TEAMS.append({'team_name': team_name, 'user_id': user_id})
    
        # Step 2: Fetch league rosters and associate with teams
    print("Fetching league rosters...")
    rosters = fetch_league_rosters(LEAGUE_ID)
    
    if not rosters:
        print("No rosters found for the league.")
        return
    
    TEAM_INFO = []

    for roster in rosters:
        roster_id = roster['roster_id']
        owner_id = roster['owner_id']
        # Find the corresponding team name and user ID
        team_info = next((team for team in TEAMS if team['user_id'] == owner_id), {"team_name": "Unknown Team", "user_id": owner_id})
        team_name = team_info['team_name']
        user_id = team_info['user_id']
        
        # Add the team info including name, user ID, and roster ID
        TEAM_INFO.append({
            'team_name': team_name,
            'user_id': user_id,
            'roster_id': roster_id
        })

    # Step 3: Print the team info including name, user ID, and roster ID
    print("\nTEAM INFORMATION:")
    for team in TEAM_INFO:
        print(f"Team Name: {team['team_name']}, User ID: {team['user_id']}, Roster ID: {team['roster_id']}")

    # Step 4: Update the team data with roster needs and drafted players
    print("Updating team data...")
    update_teams_data(rosters)
    
    # Step 5: Load and process the Excel file
    try:
        print("Loading and processing the Excel file...")
        cbs_data = load_and_process_excel(excel_file_path)
        print("Excel data loaded and processed successfully.")
        
        # Write the CBS data to a CSV file
        cbs_data.to_csv('cbs_data_output.csv', index=False)
        print("CBS data written to cbs_data_output.csv")
    except Exception as e:
        print(f"Error loading or processing Excel data: {e}")
        return

    # Step 6: Fetch data from Sleeper API
    try:
        print("Fetching data from Sleeper API...")
        sleeper_data = fetch_data_from_sleeper()
        print("Sleeper data fetched successfully.")
        
        # Write the Sleeper data to a CSV file
        sleeper_data.to_csv('sleeper_data_output.csv', index=False)
        print("Sleeper data written to sleeper_data_output.csv")
    except Exception as e:
        print(f"Error fetching Sleeper data: {e}")
        return

    # Step 7: Merge CBS data with Sleeper data
    try:
        print("Merging CBS data with Sleeper data...")
        merged_data = merge_data(cbs_data, sleeper_data)
        if merged_data is None:
            print("Process stopped due to unmatched players or defenses.")
            return
        print("Data merged successfully.")

        # Write the merged data to a CSV file
        merged_data.to_csv('merged_data_output.csv', index=False)
    except Exception as e:
        print(f"Error during data merging: {e}")
        return

    # Step 8: Identify baseline players
    try:
        print("Identifying baseline players...")
        baseline_players = identify_baseline_players(merged_data)
        print("Baseline players identified successfully.")
    except Exception as e:
        print(f"Error identifying baseline players: {e}")
        return

    # Step 9: Calculate VORP
    try:
        print("Calculating VORP scores...")
        vorp_scores = calculate_vorp(merged_data, baseline_players)
        print("VORP scores calculated successfully.")
    except Exception as e:
        print(f"Error calculating VORP scores: {e}")
        return

    # Step 10: Filter players by team needs
    try:
        print("Filtering players by team needs...")
        filtered_team_vorp_scores = filter_by_team_needs(vorp_scores, merged_data)
        print("Players filtered by team needs successfully.")
    except Exception as e:
        print(f"Error filtering players by team needs: {e}")
        return

    # Step 11: Simulate the draft for your team
    try:
        print("Simulating the draft for your team...")
        best_pick, best_total_points = simulate_draft_for_my_team(vorp_scores, TEAM_ROSTER_NEEDS, merged_data, 'Team_10')
        if best_pick is not None:
            best_pick_name = merged_data.loc[merged_data['player_id'] == best_pick, 'full_name'].values[0]
            print(f"The best pick for your team is {best_pick_name} with a projected total points of {best_total_points}.")
        else:
            print("No suitable pick found for your team.")
    except Exception as e:
        print(f"Error during draft simulation: {e}")
        return

if __name__ == "__main__":
    main()