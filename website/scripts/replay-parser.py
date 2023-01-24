"""
Author: Niklaas Cotta
Last Updated: 1/24/23
"""

import carball
import json

def extractReplayFile(pathToInput, pathToOutput):
    """
    Extracts relevant data from replay file and exports into .json
    """
    matchDataDict = carball.decompile_replay(pathToInput)
    scores = [matchDataDict['properties']['Team0Score'], matchDataDict['properties']['Team1Score']]

    extractedData = {
        "matchID": matchDataDict['properties']['Id'],
        "datePlayed" : matchDataDict['properties']['Date'],
        "team0Score": scores[0],
        "team1Score": scores[1],
        "winner": (f"team{scores.index(max(scores))}") if scores[0] != scores[1] else "tie",  # get team with highest score otherwise game was a tie
        "playerStats": matchDataDict['properties']['PlayerStats']
    }

    # Put vars into json object
    # matchDataJSON = json.dumps(extractedData, indent=4)
    matchDataJSON = json.dumps(extractedData, indent=4)

    # Put json object into file
    with open(pathToOutput, "w") as outfile:
        outfile.write(matchDataJSON)


# Example of use
extractReplayFile("./match.replay", "./website/data/match.json")
