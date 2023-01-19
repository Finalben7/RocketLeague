"""
Author: Niklaas Cotta
Last Updated: 1/19/23
"""

import carball
import json

def extractReplayFile(pathToInput, pathToOutput):
    """
    Extracts relevant data from replay file and exports into .json
    """
    matchDataDict = carball.decompile_replay(pathToInput)

    extractedData = {
        "matchID": matchDataDict['properties']['Id'],
        "team0Score": matchDataDict['properties']['Team0Score'],
        "team1Score": matchDataDict['properties']['Team1Score'],
        "playerStats": matchDataDict['properties']['PlayerStats']
    }

    matchDataJSON = json.dumps(extractedData, indent=4)

    with open(pathToOutput, "w") as outfile:
        outfile.write(matchDataJSON)


# Example of use
extractReplayFile("./match.replay", "./website/data/match.json")
