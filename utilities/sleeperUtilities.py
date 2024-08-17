import requests

def fetch_projections_from_sleeper():
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        projections = {}

        for player_id, player_info in data.items():
            # Only include players with relevant fantasy positions
            if 'fantasy_positions' in player_info and player_info['fantasy_positions']:
                positions = player_info['fantasy_positions']
                # Example: Only include QB, RB, WR, TE for fantasy projections
                if any(pos in ['QB', 'RB', 'WR', 'TE'] for pos in positions):
                    projections[player_id] = {
                        'name': player_info.get('full_name', 'Unknown'),
                        'position': positions[0],  # Assume first position is primary
                        'projection': player_info.get('fantasy_data_id', 0)  # Replace with actual projection data if available
                    }

        return projections
    else:
        raise Exception(f"Failed to fetch data from Sleeper API: {response.status_code}")


# projections = fetch_projections_from_sleeper()

# def identify_baseline_players(projections, league_size=12):
#     baseline_players = {}
#     positions = ['QB', 'RB', 'WR', 'TE']
    
#     for position in positions:
#         players_in_position = [player for player in projections.values() if player['position'] == position]
#         players_in_position.sort(key=lambda x: x['projection'], reverse=True)
#         baseline_index = league_size - 1  # Assuming the last starter in a 12-team league
#         baseline_players[position] = players_in_position[baseline_index]['projection']
    
#     return baseline_players

# def calculate_vorp(projections, baseline_players):
#     vorp_scores = {}
    
#     for player_id, stats in projections.items():
#         position = stats['position']
#         vorp_scores[player_id] = stats['projection'] - baseline_players[position]
    
#     return vorp_scores

# baseline_players = identify_baseline_players(projections)
# vorp_scores = calculate_vorp(projections, baseline_players)

# def filter_by_team_needs(vorp_scores, projections, team_roster_needs):
#     team_filtered_players = {}
    
#     for team, needs in team_roster_needs.items():
#         team_filtered_players[team] = {player: vorp_scores[player] for player in vorp_scores if projections[player]['position'] in needs}
    
#     return team_filtered_players

# # Example team roster needs
# team_roster_needs = {
#     'Team1': ['RB', 'WR'],
#     'Team2': ['QB', 'TE'],
#     'MyTeam': ['RB', 'WR', 'TE'],
#     # Define needs for all other teams
# }

# filtered_team_vorp_scores = filter_by_team_needs(vorp_scores, projections, team_roster_needs)

# def simulate_draft_for_all_teams(vorp_scores, projections, filtered_team_vorp_scores, drafted_players, team_roster_needs):
#     simulated_draft_results = {}
    
#     # Loop through each team and simulate their pick
#     for team, filtered_scores in filtered_team_vorp_scores.items():
#         team_needs = team_roster_needs[team]
#         if team in drafted_players:
#             current_team = drafted_players[team].copy()
#         else:
#             current_team = []

#         max_total_points = 0
#         best_pick = None

#         for player, vorp in filtered_scores.items():
#             if player not in current_team:  # Check if the player is already drafted
#                 simulated_team = current_team.copy()
#                 simulated_team.append(player)

#                 # Continue picking until all positions for that team are filled
#                 for position in team_needs:
#                     if position not in [projections[p]['position'] for p in simulated_team]:
#                         remaining_players = {p: v for p, v in vorp_scores.items() if projections[p]['position'] == position}
#                         best_remaining = max(remaining_players, key=remaining_players.get)
#                         simulated_team.append(best_remaining)

#                 # Calculate total projected points for this team
#                 total_points = sum([projections[p]['projection'] for p in simulated_team])
#                 if total_points > max_total_points:
#                     max_total_points = total_points
#                     best_pick = player

#         simulated_draft_results[team] = {
#             'best_pick': best_pick,
#             'total_points': max_total_points
#         }

#     return simulated_draft_results

# drafted_players = {
#     'MyTeam': [], 
#     'Team1': [], 
#     'Team2': [],
#     # Other teams' drafted players
# }

# simulated_draft_results = simulate_draft_for_all_teams(vorp_scores, projections, filtered_team_vorp_scores, drafted_players, team_roster_needs)

# def choose_best_pick(simulated_draft_results):
#     my_team_results = simulated_draft_results['MyTeam']
#     best_pick = my_team_results['best_pick']
#     best_total_points = my_team_results['total_points']
    
#     return best_pick, best_total_points

# best_pick, best_points = choose_best_pick(simulated_draft_results)
# print(f"Best pick: {best_pick} with projected points: {best_points}")

def main():
    # Step 1: Fetch Projections from Sleeper API
    try:
        projections = fetch_projections_from_sleeper()
        print("Projections fetched successfully!")
        print(projections)
    except Exception as e:
        print(f"Error fetching projections: {e}")
    
    # # Step 2: Identify Baseline Players and Calculate VORP
    # try:
    #     league_size = 12
    #     baseline_players = identify_baseline_players(projections, league_size)
    #     vorp_scores = calculate_vorp(projections, baseline_players)
    #     print("VORP Scores calculated successfully!")
    #     print(vorp_scores)
    # except Exception as e:
    #     print(f"Error calculating VORP scores: {e}")

    # # Step 3: Filter Players by Each Team’s Roster Needs
    # try:
    #     team_roster_needs = {
    #         'Team1': ['RB', 'WR'],
    #         'Team2': ['QB', 'TE'],
    #         'MyTeam': ['RB', 'WR', 'TE'],
    #         # Define needs for all other teams
    #     }
    #     filtered_team_vorp_scores = filter_by_team_needs(vorp_scores, projections, team_roster_needs)
    #     print("Filtered VORP Scores by Team Needs:")
    #     print(filtered_team_vorp_scores)
    # except Exception as e:
    #     print(f"Error filtering by team needs: {e}")

    # # Step 4: Simulate Draft for All Teams
    # try:
    #     drafted_players = {
    #         'MyTeam': [], 
    #         'Team1': [], 
    #         'Team2': [],
    #         # Other teams' drafted players
    #     }
    #     simulated_draft_results = simulate_draft_for_all_teams(vorp_scores, projections, filtered_team_vorp_scores, drafted_players, team_roster_needs)
    #     print("Simulated Draft Results:")
    #     print(simulated_draft_results)
    # except Exception as e:
    #     print(f"Error simulating draft: {e}")

    # # Step 5: Choose the Best Pick for Your Team
    # try:
    #     best_pick, best_points = choose_best_pick(simulated_draft_results)
    #     print(f"Best pick: {best_pick} with projected points: {best_points}")
    # except Exception as e:
    #     print(f"Error choosing best pick: {e}")

if __name__ == "__main__":
    main()
