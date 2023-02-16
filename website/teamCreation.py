from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from . import db
from flask_login import login_user, login_required, logout_user, current_user

"""
Outlines:
    Team Creation
    - A team is a collection of players (2, 3, ...?) 
        - Should team be collection of player objects or just user_id strings?
        - Should we assume team captain is creator of team?
    - Each player has a rank (players will input own rank)
    - The Team rank is the same rank as the highest-ranked player on the team
    - Each team object will have a teamID, teamRank, teamCaptain, teamName, and region


    Rank Queue
    - Once team has been created, team can see list of queues and join a queue (FIFO)
    - Queues are rank-specific
    - When there are 8 teams in the queue, a new league will be created
    - Generate bracket from teams in queue
    - Matches will be held, then user will submit score manually OR we parse for score
    - Update bracket based on scores until there is a winner
"""

############################# Nik's Code #############################

def createTeam():
    newTeam = Team()
    team.id = random.randint()
    team.players.append(teamCreator)
    team.players.append(player2, player3)
    team.rank = max(team.players.rank)
    team.captain = teamCreator.userID
    team.region = teamCreator.region
    
    return newTeam
    
def submitTeam(team):
    if len(team.players) != 3:
        flash("Team does not have three members", category='error')
        return False
    
    db.session.add(team)
    db.session.commit()
    
    return True
    
def viewQueues():
    for queue in queues:
        display(queue.teams, queue.rank)

def joinQueue(team, queue):
    if team.rank != queue.rank:
        flash("Team is not the correct rank for this queue", category='error')
        return False
    
    queue.append(team)
    return True

def createLeague(queue):
    while len(queue < 8):
        wait()
    
    league = generateBracket(queue)
    
    return league

def matchListener(match):  # Event listener
    while not matchFinished:
        wait()
    
    team0.score = input()
    team1.score = input()

    if team0.score > team1.score:
        winner = team0
        loser = team1
    elif team0.score < team1.score:
        winner = team1
        loser = team0
    else:
        winner = "tie"
        # how do we treat ties for bracket?
        
    return winner

def leagueListener(league):
    # Multithread?
    winners = []
    for match in league:
        winners.append(matchListener(match))
    
    updateBracket(winners)



######################### Ben's Initial Code #########################

logic = Blueprint('logic', __name__)

#Team creation
@logic.route('/createTeam', methods=['GET', 'POST'])
def createTeam():
    if request.method == 'POST':
        userID = request.form.get('userID')
        userRank = request.form.get('userRank')
        team = []
        team.append(userID)
        teamRanks = []
        teamRanks.append(userRank)
        teamRank = max(teamRanks)
    if team.__len__ == 3:
        for userID in team:
            newTeam = teams(teamID = teamID, userID = userID, teamRank = teamRank)
            db.session.add = newTeam(teams)
            db.session.commit()

#Queue and league generation logic
@logic.route('/joinQueue', methods=['GET', 'POST'])
def joinQueue():
    if request.method == 'POST':
        teamID = request.form.get('teamID')
        teamName = request.form.get('teamName')
        record = request.form.get('record')
        queue = []
        queue.append(teamID)
    if queue.__len__ == 8:
        for teamID in queue:
            newLeague = league(teamID = teamID, teamName = teamName, record = record)
            db.session.add = newLeague(league)
            db.session.commit()
