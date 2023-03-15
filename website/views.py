from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import User, Team, TeamPlayers, League, Series
from . import db
from sqlalchemy import text, func

views = Blueprint('views', __name__)

@views.route('/')
#@login_required
def home():
    return render_template('index.html', user=current_user)

@views.route('/profile')
def profile():
    return render_template('profile.html', user=current_user)

@views.route('/teams')
def teams():
    #Create a variable to store current_users id for use in query
    current_user_id = current_user.id
    #Find all usernames from each teamId associated with the current_user.id's teamId's (that's a mouthful)
    query = f'''
        SELECT u.username, t.teamName
        FROM User u
        INNER JOIN TeamPlayers tp ON u.id = tp.userId
        INNER JOIN Team t ON tp.teamId = t.id
        WHERE tp.teamId IN (
            SELECT tp2.teamId
            FROM TeamPlayers tp2
            WHERE tp2.userId = {current_user_id}
        );
    '''
    with db.engine.connect() as con:
        result = con.execute(query)
        teams = result.fetchall()
        #Store the results of the query in a dictionary to make data easier to access with Jinja
        team_users = {}
        for team in teams:
            team_name = team['teamName']
            if team_name not in team_users:
                team_users[team_name] = []
            team_users[team_name].append(team['username'])
    return render_template('teams.html', user=current_user, teams=team_users)

@views.route('/team')
def team():
    team_name = request.args.get('team')
    # Find team with matching teamName passed through args
    team = Team.query.filter(Team.teamName == team_name).first()
    # Fetch the players for the team
    players = User.query.join(TeamPlayers).join(Team).filter(Team.teamName == team_name).all()
    # Get a list of usernames for the players
    usernames = [player.username for player in players]

    # Check if team isActive, if not render joinQueue button and numberInQueue
    if team.isActive == False:
        query = f'''
            SELECT t.id, t.rank, t.region, t.isQueued
            FROM Team t
            WHERE t.isQueued = 1
        '''
        with db.engine.connect() as conn:
            teamsList = conn.execute(query).fetchall()
        # Filter out teams that don't match current teams rank and region
        filteredTeams = [t for t in teamsList if ((t.rank == team.rank) and (t.region == team.region) and (t.isQueued))]
        numberInQueue = len(filteredTeams)

        # Render the team page template and pass in the team and players objects
        return render_template('team.html', user=current_user, current_team=team, usernames=usernames, numberInQueue=numberInQueue)
    # If team isActive get team names for bracket
    else: #FIXME: Add logic to make this specific to teams within certain leagues
        query = f'''
         SELECT t.id, t.teamName
         FROM Team t
         WHERE t.isActive = 1
    '''
    with db.engine.connect() as conn:
        team_data = conn.execute(query).fetchall()
    # Store teamNames is a list to remove quotations and parenthesis
        team_names = [data[1] for data in team_data]
        team_ids = [data[0] for data in team_data]
    # Pair teamNames together to create matches
    match1 = {"team0" : team_names[0], "team1" : team_names[1]}
    match2 = {"team0" : team_names[2], "team1" : team_names[3]}
    match3 = {"team0" : "TBD", "team1" : "TBD"}
    # Check to see if any team is a seriesWinner, if yes add them to match 3
    winners = f'''
            SELECT s.seriesWinner, t.teamName
            FROM Series s
            JOIN Team t ON s.seriesWinner = t.id
        '''
    with db.engine.connect() as conn:
        series_winners = conn.execute(winners).fetchall()
    
    # Filter winners that don't match current team_ids
    filteredWinners = [s for s in series_winners if s.seriesWinner in team_ids]

    winner_names = [w[1] for w in filteredWinners]
    print(winner_names)

    if len(filteredWinners) == 1:
        if winner_names[0] in (match1['team0'], match1['team1']):
            match3['team0'] = winner_names[0]
        else:
            match3['team1'] = winner_names[0]

    if len(filteredWinners) == 2:
        if winner_names[0] in (match1['team0'], match1['team1']):
            match3['team0'] = winner_names[0]
            match3['team1'] = winner_names[1]
        else:
            match3['team0'] = winner_names[1]
            match3['team1'] = winner_names[0]
    # Store matches is bracket dictionary
    bracket = {"match1" : match1, "match2" : match2, "match3" : match3}
    # Search bracket for current team_name passed through args to find their opponent team name
    for match_name, match in bracket.items():
        # check if the team_name is in the match dictionary values
        if team_name in match.values():
            # get the key associated with the other team name
            other_team_key = [key for key, value in match.items() if value != team_name][0]
            # get the other team name from the match dictionary using the key
            opponent_team = match[other_team_key]
            # return the other team name
    return render_template('team.html', user=current_user, current_team=team, opponent_team=opponent_team, bracket=bracket, usernames=usernames)

@views.route('/match')
def match():
    return render_template('match.html', user=current_user)

@views.route('/submitScore')
def submitScore():
    # Get Team.teamNames from args
    current_team_name = request.args.get('current_team')
    opponent_team_name = request.args.get('opponent_team')

    # Get Team from db with matching teamNames
    current_team = Team.query.filter_by(teamName=current_team_name).first()
    opponent_team = Team.query.filter_by(teamName=opponent_team_name).first()

    # Get Users associated with Team.Id's from TeamPlayes
    current_team_users = User.query.join(TeamPlayers).filter_by(teamId=current_team.id).all()
    opponent_team_users = User.query.join(TeamPlayers).filter_by(teamId=opponent_team.id).all()

    # Store Team.id with User.usernames inside
    current_team_dict = {'teamId': current_team.id, 'usernames': [user.username for user in current_team_users]}
    opponent_team_dict = {'teamId': opponent_team.id, 'usernames': [user.username for user in opponent_team_users]}

    return render_template('submitScore.html', user=current_user, current_team_dict=current_team_dict, opponent_team_dict=opponent_team_dict, current_team_name=current_team_name, opponent_team_name=opponent_team_name)

@views.route('/league')
def league():
    return render_template('league.html', user=current_user)

# @views.route('/bracket') #FIXME: Add logic to make this specific to teams/leagues
# def bracket():
#     query = f'''
#          SELECT t.teamName
#          FROM Team t
#          WHERE t.isActive = 1
#     '''
#     with db.engine.connect() as conn:
#         teamsList = conn.execute(query).fetchall()

#     teams = [team['teamName'] for team in teamsList]

#     return render_template('bracket.html', user=current_user, team=teams)

@views.route('/createTeam')
def createTeam():
    return render_template('createTeam.html', user=current_user)

@views.route('/joinQueue')
def joinQueue():
    # Find team that current_user is captain of with matching teamName passed through args
    team = Team.query.filter(Team.teamCaptain == current_user.id, Team.teamName == request.args.get('team')).first()
    
    # Store teamName in variable
    teamName = request.args.get('team')

    # Check to see if user who clicked joinQueue is a captain
    if team is None:
        flash("Only the captain of the team can join the queue.", category="error")
        return redirect(url_for('views.teams'))
    # Check to see if team is aleary in a league with the same rank/region combination    
    if team and team.isQueued or team.isActive:
        flash(f"{teamName} is already queued or active in this rank and region.", category="error")
        return redirect(url_for('views.teams'))
    # If not change isQueued = true
    if team:
        team.isQueued = True
        db.session.commit()

        # Count number of teams in queue for current team's rank/region
        count = Team.query.filter_by(rank=team.rank, region=team.region, isQueued=True).count()
        flash(f"{teamName} has been added to the queue. Position:{count}/4", category="success")

        # Queue is full, add teams to league
        if count == 4:
            # Get all teams in the queue
            queued_teams = Team.query.filter_by(rank=team.rank, region=team.region, isQueued=True).all()
            
            # Set isQueued = False and isActive = True for each team
            for t in queued_teams:
                t.isQueued = False
                t.isActive = True

            # Get the latest league.id
            last_id = db.session.query(func.coalesce(func.max(League.id), 0)).scalar()

            # Increment the league.id by 1
            new_id = last_id + 1

            # Create League entries for each team
            league_entries = [League(id=new_id, team_id=t.id) for t in queued_teams]
            
            # Add the League entries to the database
            db.session.add_all(league_entries)
            db.session.commit()
            
            flash("Queue is now full and bracket will be generated!", category="success")
    else:
        # Handle the case where no matching team is found
        flash("Unable to find the specified team.", category="error")

    return redirect(url_for('views.teams'))
