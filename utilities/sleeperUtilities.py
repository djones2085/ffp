import requests

# Global Constants

# POSITIONS: List of relevant fantasy football positions
# Used to filter and identify players that are of interest for fantasy projections.
POSITIONS = ['QB', 'RB', 'WR', 'TE']

# LEAGUE_SIZE: Integer representing the number of teams in the league
# This determines how many players at each position are considered starters, 
# which affects baseline player calculations and draft strategies.
LEAGUE_SIZE = 12

# TEAM_ROSTER_NEEDS: Dictionary mapping each team to a list of positions they need to fill
# The keys are team names, and the values are lists of positions that the team needs to draft.
# This is used to filter players based on the specific needs of each team during the draft simulation.
TEAM_ROSTER_NEEDS = {
    'Team1': ['RB', 'WR'],   # Team1 needs a Running Back (RB) and a Wide Receiver (WR)
    'Team2': ['QB', 'TE'],   # Team2 needs a Quarterback (QB) and a Tight End (TE)
    'MyTeam': ['RB', 'WR', 'TE'],  # MyTeam needs a Running Back, Wide Receiver, and Tight End
}

# DRAFTED_PLAYERS: Dictionary mapping each team to a list of player IDs that have already been drafted
# The keys are team names, and the values are lists of player IDs representing the players that the team has already drafted.
# This is used during the draft simulation to avoid drafting the same player multiple times.
DRAFTED_PLAYERS = {
    'MyTeam': [],   # List of player IDs drafted by MyTeam
    'Team1': [],    # List of player IDs drafted by Team1
    'Team2': [],    # List of player IDs drafted by Team2
}


def fetch_projections_from_sleeper():
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        projections = {}

        for player_id, player_info in data.items():
            if 'fantasy_positions' in player_info and player_info['fantasy_positions']:
                positions = player_info['fantasy_positions']
                if any(pos in POSITIONS for pos in positions):
                    projections[player_id] = {
                        'name': player_info.get('full_name', 'Unknown'),
                        'position': positions[0],
                        'projection': player_info.get('fantasy_data_id', 0)
                    }

        return projections
    else:
        raise Exception(f"Failed to fetch data from Sleeper API: {response.status_code}")

def identify_baseline_players(projections):
    baseline_players = {}
    
    for position in POSITIONS:
        players_in_position = [player for player in projections.values() if player['position'] == position]
        players_in_position.sort(key=lambda x: x['projection'], reverse=True)
        
        if len(players_in_position) > 0:
            baseline_index = min(LEAGUE_SIZE - 1, len(players_in_position) - 1)
            baseline_players[position] = players_in_position[baseline_index]['projection']
        else:
            baseline_players[position] = 0

    return baseline_players

def calculate_vorp(projections, baseline_players):
    vorp_scores = {}
    
    for player_id, stats in projections.items():
        position = stats['position']
        vorp_scores[player_id] = stats['projection'] - baseline_players[position]
    
    return vorp_scores

def filter_by_team_needs(vorp_scores, projections):
    team_filtered_players = {}
    
    for team, needs in TEAM_ROSTER_NEEDS.items():
        team_filtered_players[team] = {player: vorp_scores[player] for player in vorp_scores if projections[player]['position'] in needs}
    
    return team_filtered_players

def simulate_draft_for_all_teams(vorp_scores, projections, filtered_team_vorp_scores):
    simulated_draft_results = {}
    
    for team, filtered_scores in filtered_team_vorp_scores.items():
        team_needs = TEAM_ROSTER_NEEDS[team]
        if team in DRAFTED_PLAYERS:
            current_team = DRAFTED_PLAYERS[team].copy()
        else:
            current_team = []

        max_total_points = 0
        best_pick = None

        for player, vorp in filtered_scores.items():
            if player not in current_team:
                simulated_team = current_team.copy()
                simulated_team.append(player)

                for position in team_needs:
                    if position not in [projections[p]['position'] for p in simulated_team]:
                        remaining_players = {p: v for p, v in vorp_scores.items() if projections[p]['position'] == position}
                        best_remaining = max(remaining_players, key=remaining_players.get)
                        simulated_team.append(best_remaining)

                total_points = sum([projections[p]['projection'] for p in simulated_team])
                if total_points > max_total_points:
                    max_total_points = total_points
                    best_pick = player

        simulated_draft_results[team] = {
            'best_pick': best_pick,
            'total_points': max_total_points
        }

    return simulated_draft_results

def choose_best_pick(simulated_draft_results):
    my_team_results = simulated_draft_results['MyTeam']
    best_pick = my_team_results['best_pick']
    best_total_points = my_team_results['total_points']
    
    return best_pick, best_total_points

def main():
    try:
        projections = fetch_projections_from_sleeper()
        print("Projections fetched successfully!")
    except Exception as e:
        print(f"Error fetching projections: {e}")
        return
    
    try:
        baseline_players = identify_baseline_players(projections)
        vorp_scores = calculate_vorp(projections, baseline_players)
        print("VORP Scores calculated successfully!")
    except Exception as e:
        print(f"Error calculating VORP scores: {e}")
        return

    try:
        filtered_team_vorp_scores = filter_by_team_needs(vorp_scores, projections)
        print("Filtered VORP Scores by Team Needs:")
    except Exception as e:
        print(f"Error filtering by team needs: {e}")
        return

    try:
        simulated_draft_results = simulate_draft_for_all_teams(vorp_scores, projections, filtered_team_vorp_scores)
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
