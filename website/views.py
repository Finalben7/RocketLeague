from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from .models import User, Team, TeamPlayers
from . import db
from sqlalchemy import text

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
    print(teams)
    return render_template('teams.html', user=current_user, teams=team_users)

@views.route('/team')
def team():
    team = request.args.get('team')
    # Fetch the players for the team
    players = User.query.join(TeamPlayers).join(Team).filter(Team.teamName == team).all()
    # Get a list of usernames for the players
    usernames = [player.username for player in players]
    # Render the team page template and pass in the team and players objects
    return render_template('team.html', user=current_user, team=team, usernames=usernames)

@views.route('/match')
def match():
    return render_template('match.html', user=current_user)

@views.route('/submitScore')
def submitScore():
    return render_template('submitScore.html', user=current_user)

@views.route('/league')
def league():
    return render_template('league.html', user=current_user)

@views.route('/bracket')
def bracket():
    return render_template('bracket.html', user=current_user)

@views.route('/createTeam')
def createTeam():
    return render_template('createTeam.html', user=current_user)

@views.route('/joinQueue')
def joinQueue():
    team = request.args.get('team')
    usernames = request.args.get('usernames')
    print("joinQueue called!")
    return redirect(url_for('views.team', team=team, usernames=usernames))
