from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User, Team, TeamPlayers
from . import db
from flask_login import login_user, login_required, logout_user, current_user

logic = Blueprint('logic', __name__)

#Team creation
@logic.route('/createTeam', methods=['GET', 'POST'])
def createTeam():
    if request.method == 'POST':
        #Get data from form and DB to store in variables
        captainID = current_user.id
        teamName = request.form.get('teamName')
        teamRegion = request.form.get('region')
        userOneNameForm = request.form.get('userOneName')
        userOneIdForm = request.form.get('userOneId')
        userOne = User.query.filter_by(username=userOneNameForm, id=userOneIdForm).first()
        #Validate team members exist
        if userOne is not None:
            #Validate user did not enter themself
            if userOne.id == captainID:
                flash('You cant be your own teammate...', category='error')
                return render_template('createTeam.html', user=current_user)        
            #Get ranks from captain and the entered user and take the larger of the two to define the team rank
            rank1 = current_user.rank
            rank2 = userOne.rank
            teamRank = max(rank1, rank2)
            #Validate the user doesn't already have a team with the exact same region/rank combination
            teamCheckOne = Team.query.filter_by(teamCaptain=captainID, region=teamRegion, rank=teamRank)
            teamCheckTwo = Team.query.filter_by(teamCaptain=userOne.id, region=teamRegion, rank=teamRank)
            if teamCheckOne is not None or teamCheckTwo is not None:
                flash('You, or your teammate, already have a team in this division', category='error')
                return render_template('createTeam.html', user=current_user) 
            #Create a new Team with the validated data
            newTeam = Team(teamCaptain=captainID, teamName=teamName, region=teamRegion, rank=teamRank)
            db.session.add(newTeam)
            db.session.commit()
            #Get the teamId of the newly created team, store it in a variable and pass that data to the teamPlayers table as well
            teamId = newTeam.id
            print(teamId)
            teamPlayers1 = TeamPlayers(userId=captainID, teamId=teamId)
            teamPlayers2 = TeamPlayers(userId=userOne.id, teamId=teamId)
            db.session.add_all([teamPlayers1, teamPlayers2])
            db.session.commit()
            flash('Team Created!', category='success')
            return render_template('teams.html', user=current_user)
        else: flash('The teammate information you entered is not valid, please double check the form.', category='error')
        return render_template('createTeam.html', user=current_user)

#Queue and league generation logic
#@logic.route('/joinQueue', methods=['GET', 'POST'])
#def joinQueue():
#    if request.method == 'POST':
#        teamID = request.form.get('teamID')
#        teamName = request.form.get('teamName')
#        record = request.form.get('record')
#        queue = []
#        queue.append(teamID)
#    if queue.__len__ == 8:
#        for teamID in queue:
#            newLeague = league(teamID = teamID, teamName = teamName, record = record)
#            db.session.add = newLeague(league)
#            db.session.commit()