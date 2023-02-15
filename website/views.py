from flask import Blueprint, render_template
from flask_login import login_required, current_user

views = Blueprint('views', __name__)

# Home page for root
@views.route('/')
#@login_required
def home():
    return render_template('index.html', user=current_user)

@views.route('/profile')
def profile():
    return render_template('profile.html', user=current_user)

@views.route('/teams')
def teams():
    return render_template('teams.html', user=current_user)

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