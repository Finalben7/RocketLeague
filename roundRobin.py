# Get Team id's from database with matching ranks/regions and where Team.isQueued = True
queuedTeams = [0,1,2,3,4,5,6,7]
# Create list of checkpoints so the series iterator knows when to move to the next set of team id's in queuedTeams
checkpoints = [7,13,18,22,25,27,28]
# Modify the order Series id's are used to create a logical schedule ensuring each team only has one match per week when all matches are sorted by Series.id
seriesModifier = [1,5,9,13,17,21,25,10,6,18,14,26,22,2,23,27,15,19,28,24,20,16,3,7,11,12,8,4]
# Set initial values for variables used in the for loops and create empty results list to be populated later
s = 0
m = 0
n = 1
x = 1
results = []

# An 8 team round robin has 28 unique matchups, this loop will create a new seriesId for each matchup using the seriesModifier list to ensure the correct order is used
for i in range(1, 29):
    seriesId = s + seriesModifier[i-1]
# This loop creates 5 identical "matches" since each match is a best of 5
    for j in range(1, 6):
# Create a dictionary containing seriesId, team1 and team2
        result_entry = {
            'seriesId': seriesId,
            'team1': queuedTeams[m],
            'team2': queuedTeams[n]
        }
# Nest dictionaries inside of results list
        results.append(result_entry)
# Increment team2 by 1 each time through the loop to create a unique matchup
    n += 1
# After checkpoint(s)[0] increment team1 by 1 and team2 by 1 plus the number of times looped 
    if i in checkpoints:
        m += 1
        n = 1 + x
        x += 1

# Sort the results list by seriesId ASC
sorted_results = sorted(results, key=lambda x: x['seriesId'])

# Now you can access and work with the sorted_results list
for entry in sorted_results:
    print(entry)