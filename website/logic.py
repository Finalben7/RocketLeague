from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User, Team, TeamPlayers, Stats, Series
from . import db
from flask_login import current_user
from sqlalchemy import func
from collections import Counter

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
            teamCheckOne = Team.query.filter(Team.teamCaptain == captainID, Team.region == teamRegion, Team.rank == teamRank).first()
            teamCheckTwo = Team.query.filter(Team.teamCaptain == userOne.id, Team.region == teamRegion, Team.rank == teamRank).first()
            if teamCheckOne is not None or teamCheckTwo is not None:
                flash('You, or your teammate, already have a team in this division', category='error')
                return render_template('createTeam.html', user=current_user) 
            #Create a new Team with the validated data
            newTeam = Team(teamCaptain=captainID, teamName=teamName, region=teamRegion, rank=teamRank)
            db.session.add(newTeam)
            db.session.commit()
            #Get the teamId of the newly created team, store it in a variable and pass that data to the teamPlayers table as well
            teamId = newTeam.id
            teamPlayers1 = TeamPlayers(userId=captainID, teamId=teamId)
            teamPlayers2 = TeamPlayers(userId=userOne.id, teamId=teamId)
            db.session.add_all([teamPlayers1, teamPlayers2])
            db.session.commit()
            flash('Team Created!', category='success')
            return redirect(url_for('views.teams', user=current_user))
        else: flash('The teammate information you entered is not valid, please double check the form.', category='error')
        return render_template('createTeam.html', user=current_user)

# Score submission
@logic.route('/submitScore', methods=['GET', 'POST'])
def submitScore():
    if request.method == 'POST':
        # Get Team.id's from form
        winners = [int(request.form.get('gameOneWinner')), int(request.form.get('gameTwoWinner')), int(request.form.get('gameThreeWinner'))]

        # Check to make sure that all three values are not the same
        if len(set(winners)) == 1:
            flash("One team cannot win all 3 games in a best of 3, please try again.", category="error")
            return redirect(request.referrer)
        
        # Check if game 3 has a winner for no reason
        if winners[0] == winners[1] and winners[2] != 0:
            flash("Game 3 cannot have a winner if the series is over after two games.", category="error")
            return redirect(request.referrer)

        # Remove and 0 values from the winner list
        winners = [i for i in winners if i !=0]

        # Get the series winner
        winnerCount = Counter(winners)
        seriesWinner = winnerCount.most_common(1)[0][0]

        # Get the latest Series.id
        last_id = db.session.query(func.coalesce(func.max(Series.id), 0)).scalar()
        
        # Increment the Series.id by 1
        new_id = last_id + 1

        # Enter series id in table
        series_entry = [Series(id=new_id, seriesWinner=seriesWinner)]
        db.session.add_all(series_entry)

        # Create new Stats entries for each winning team
        for team_id in winners:
            if team_id:
                new_stats_entry = Stats(Series_id=new_id, winningTeam=team_id)
                db.session.add(new_stats_entry)
        db.session.commit()
        flash("Results submitted!", category="success")
        return redirect(url_for('views.teams'))