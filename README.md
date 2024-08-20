# Fantasy Football Picker

## Fantasy Football Draft Simulator

This Python program simulates a fantasy football draft using player projections and value-over-replacement-player (VORP) calculations. The program allows you to fetch player data from the Sleeper API, calculate baseline players for each position, and simulate a draft to determine the best picks for each round based on team needs.

## Table of Contents

- [Overview](#overview)
- [Global Constants](#global-constants)
- [Functions](#functions)
  - [fetch_projections_from_sleeper()](#fetch_projections_from_sleeper)
  - [identify_baseline_players(projections)](#identify_baseline_playersprojections)
  - [calculate_vorp(projections, baseline_players)](#calculate_vorpprojections-baseline_players)
  - [filter_by_team_needs(vorp_scores, projections)](#filter_by_team_needsvorp_scores-projections)
  - [simulate_draft_for_all_teams(vorp_scores, projections, filtered_team_vorp_scores)](#simulate_draft_for_all_teamsvorp_scores-projections-filtered_team_vorp_scores)
  - [choose_best_pick(simulated_draft_results)](#choose_best_picksimulated_draft_results)
  - [main()](#main)

## Overview

The program is designed to help fantasy football players make informed draft decisions by simulating a draft process and providing recommendations based on projected player performance. It uses data fetched from the Sleeper API to perform various calculations and simulate draft scenarios. The program consists of several key functions that work together to identify the best possible draft picks for each team based on their specific needs.

## Global Constants

### POSITIONS
- **Format:** `List[str]`
- **Example:** `['QB', 'RB', 'WR', 'TE']`
- **Description:** A list of relevant fantasy football positions. This list is used to filter and identify players that are of interest for fantasy projections.

### LEAGUE_SIZE
- **Format:** `int`
- **Example:** `12`
- **Description:** The number of teams in the league. This variable determines how many players at each position are considered starters, which affects baseline player calculations and draft strategies.

### TEAM_ROSTER_NEEDS
- **Format:** `Dict[str, List[str]]`
- **Example:** 
  ```python
  {
      'Team1': ['RB', 'WR'],
      'Team2': ['QB', 'TE'],
      'MyTeam': ['RB', 'WR', 'TE'],
  }
Description: A dictionary mapping each team to a list of positions they need to fill. This is used to filter players based on the specific needs of each team during the draft simulation.
DRAFTED_PLAYERS
Format: Dict[str, List[str]]
Example:
python
Copy code
{
    'MyTeam': [], 
    'Team1': [], 
    'Team2': [],
}
Description: A dictionary mapping each team to a list of player IDs that have already been drafted. This is used during the draft simulation to avoid drafting the same player multiple times.
Functions

fetch_projections_from_sleeper()
Parameters: None
Returns: Dict[str, Dict]
Description:
Fetches player data from the Sleeper API.
Filters players based on the relevant fantasy positions defined in the POSITIONS global constant.
Returns a dictionary where each key is a player ID, and each value is another dictionary containing the player's name, primary position, and projection (placeholder for now).
identify_baseline_players(projections)
Parameters:
projections (Dict[str, Dict]): A dictionary of player projections, typically returned from fetch_projections_from_sleeper().
Returns: Dict[str, float]
Description:
Identifies the baseline player for each position based on the LEAGUE_SIZE.
The baseline player is generally the last starter in a given league size.
Returns a dictionary where each key is a position (e.g., 'QB', 'RB') and each value is the projection of the baseline player for that position.
calculate_vorp(projections, baseline_players)
Parameters:
projections (Dict[str, Dict]): A dictionary of player projections.
baseline_players (Dict[str, float]): A dictionary of baseline player projections for each position.
Returns: Dict[str, float]
Description:
Calculates the Value Over Replacement Player (VORP) for each player.
VORP is calculated as the difference between a player's projection and the projection of the baseline player at the same position.
Returns a dictionary where each key is a player ID and each value is that player's VORP score.
filter_by_team_needs(vorp_scores, projections)
Parameters:
vorp_scores (Dict[str, float]): A dictionary of VORP scores for each player.
projections (Dict[str, Dict]): A dictionary of player projections.
Returns: Dict[str, Dict[str, float]]
Description:
Filters players based on the specific roster needs of each team.
Uses the TEAM_ROSTER_NEEDS global constant to determine which positions each team needs.
Returns a dictionary where each key is a team name, and each value is another dictionary mapping player IDs to their VORP scores.
simulate_draft_for_all_teams(vorp_scores, projections, filtered_team_vorp_scores)
Parameters:
vorp_scores (Dict[str, float]): A dictionary of VORP scores for each player.
projections (Dict[str, Dict]): A dictionary of player projections.
filtered_team_vorp_scores (Dict[str, Dict[str, float]]): A dictionary of filtered VORP scores for each team, based on their specific needs.
Returns: Dict[str, Dict[str, Union[str, float]]]
Description:
Simulates a draft for all teams, selecting players based on their VORP scores and the team's specific needs.
Uses the DRAFTED_PLAYERS global constant to track which players have already been selected.
Returns a dictionary where each key is a team name, and each value is another dictionary containing the best pick and the team's total projected points after the simulated draft.
choose_best_pick(simulated_draft_results)
Parameters:
simulated_draft_results (Dict[str, Dict[str, Union[str, float]]): The results of the simulated draft, typically returned from simulate_draft_for_all_teams().
Returns: Tuple[str, float]
Description:
Determines the best pick for "MyTeam" based on the simulated draft results.
Returns a tuple containing the best player's ID and the total projected points for "MyTeam" if that player is selected.
main()
Parameters: None
Returns: None
Description:
The main function that orchestrates the entire draft simulation process.
Fetches player projections, calculates baseline players and VORP scores, filters players based on team needs, simulates a draft, and then determines the best pick for "MyTeam".
Outputs the results of each step to the console.
Usage

To run the program, simply execute the sleeperUtilities.py script. The script will automatically run the main() function, which handles the entire draft simulation process. Ensure that the Sleeper API is accessible and that the necessary Python packages (requests) are installed.
bash
Copy code
python3 sleeperUtilities.py
This program is designed to be customizable, so feel free to adjust the global constants and input data as needed to fit your specific fantasy football league.
License

This project is licensed under the MIT License - see the LICENSE file for details.
markdown
Copy code

### Summary of the README
- **Overview**: Provides a high-level understanding of what the program does.
- **Global Constants**: Details the format and usage of each global variable in the script.
- **Functions**: Describes each function, its parameters, return values, and how it contributes to the overall program.
- **Usage**: Gives instructions on how to run the program.
- **License**: Placeholder for licensing information.

This README should give users and developers a clear understanding of how the program works, how to use it, and how to modify it if needed.