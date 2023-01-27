from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from . import db
from flask_login import login_user, login_required, logout_user, current_user

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
