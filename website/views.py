from flask import Blueprint, render_template
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
    current_user_id = current_user.id  # Replace with your current user ID
    query = f'''
        SELECT u.username, t.teamName, t.rank, t.region
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
    print(teams)
    return render_template('teams.html', user=current_user, teams=teams)

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
    return render_template('beta-bracket.html', user=current_user)

@views.route('/createTeam')
def createTeam():
    return render_template('createTeam.html', user=current_user)