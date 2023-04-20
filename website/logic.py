from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User, Team, TeamPlayers, Stats, Series, League
from . import db
from flask_login import current_user
from sqlalchemy import text, update, and_, or_, func
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

        # # Get the series winner
        winnerCount = Counter(winners)
        seriesWinner = winnerCount.most_common(1)[0][0]

        # Get League.id, Series_id and Team.id's from args
        current_league_id = request.form['current_league_id']
        series_id = request.form['series_id']
        # current_team_id = request.form['current_team_id']
        # opponent_team_id = request.form['opponent_team_id']

        # WHERE clause for update queries
        where_clause = Stats.Series_id == series_id

        # Check if there are exactly 2 or 3 winners
        if len(winners) in [2, 3]:
            # Get the rows to update
            stats_to_update = db.session.query(Stats).filter(where_clause).limit(len(winners)).all()

            # Update winningTeam for each row
            for i, stat in enumerate(stats_to_update):
                if winners[i] != 0:
                    stat.winningTeam = winners[i]

            # Get Series to update
            series = Series.query.filter(Series.id == stats_to_update[0].Series_id).first()

            # Update seriesWinner in Series table
            series.seriesWinner = seriesWinner

            db.session.commit()

            # Check to see if all season series have been played
            seasonQuery = text(f'''
                SELECT DISTINCT Team0_id, Team1_id, winningTeam 
                    FROM Stats 
                    WHERE League_id = {current_league_id} AND round_one = 0 AND round_two = 0 AND round_three = 0
                    GROUP BY Team0_id, Team1_id;
            ''')
            with db.engine.connect() as conn:
                seasonSeries = conn.execute(seasonQuery).fetchall()

            seasonIsComplete = all(series.winningTeam is not None for series in seasonSeries)

            # Check to see if round_one has already been generated
            roundOneQuery = text(f'''
                SELECT DISTINCT Team0_id, Team1_id, winningTeam 
                    FROM Stats 
                    WHERE League_id = {current_league_id} AND round_one = 1
                    GROUP BY Team0_id, Team1_id;
            ''')
            with db.engine.connect() as conn:
                roundOneSeries = conn.execute(roundOneQuery).fetchall()

            if seasonIsComplete and not roundOneSeries:

                # Change isPlayoffs = True for all teams with matching current League.id
                db.session.query(League).filter(League.id == current_league_id).update({"isPlayoffs": True})
                db.session.commit()

                # Count the number of wins each Team.id appears in Stats.winningTeam with the matching League.id
                results = db.session.query(
                    Stats.winningTeam, func.count()
                ).filter(
                    Stats.League_id == current_league_id,
                    Stats.winningTeam.isnot(None)
                ).group_by(
                    Stats.winningTeam
                ).order_by(func.count().desc()
                ).all()

                # Get the latest Series.id
                last_series_id = db.session.query(func.coalesce(func.max(Series.id), 0)).scalar()

                # Create matches in Stats table for each round_one matchup
                m = 0
                n = 7
                for i in range(1,5):
                    series = Series()
                    series.id = last_series_id + i
                    db.session.add(series)
                    for j in range(1,4):
                        stat = Stats()
                        stat.League_id = current_league_id
                        stat.Series_id = series.id
                        stat.Team0_id = results[m][0]
                        stat.Team1_id = results[n][0]
                        stat.round_one = True
                        db.session.add(stat)
                    m+=1
                    n-=1
                print("Round 1 matches created!")
                db.session.commit()
                flash("Results submitted!", category="success")
                return redirect(url_for('views.teams'))
            
            # Check to see if all of playoffs round_one series have been played
            playoffsRoundOneIsComplete = all(series.winningTeam is not None for series in roundOneSeries)

            # Check to see if round_two has already been generated
            roundTwoQuery = text(f'''
                SELECT DISTINCT Team0_id, Team1_id, winningTeam 
                    FROM Stats 
                    WHERE League_id = {current_league_id} AND round_two = 1
                    GROUP BY Team0_id, Team1_id;
            ''')
            with db.engine.connect() as conn:
                roundTwoSeries = conn.execute(roundTwoQuery).fetchall()

            if playoffsRoundOneIsComplete and not roundTwoSeries:

                # Get the latest Series.id
                last_series_id = db.session.query(func.coalesce(func.max(Series.id), 0)).scalar()

                # Count the number of wins each Team.id appears in Stats.winningTeam with the matching League.id and round_one = True
                results = db.session.query(
                    Stats.winningTeam, Stats.Series_id, func.count()
                ).filter(
                    Stats.League_id == current_league_id,
                    Stats.winningTeam.isnot(None),
                    Stats.round_one == 1
                ).group_by(
                    Stats.winningTeam, Stats.Series_id
                ).having(
                    func.count(Stats.winningTeam) == 2
                ).order_by(
                    Stats.Series_id.asc()
                ).all()

                # Create matches in Stats table for each round_two matchup
                m = 0
                n = 3
                for i in range(1,3):
                    series = Series()
                    series.id = last_series_id + i
                    db.session.add(series)
                    for j in range(1,4):
                        stat = Stats()
                        stat.League_id = current_league_id
                        stat.Series_id = series.id
                        stat.Team0_id = results[m][0]
                        stat.Team1_id = results[n][0]
                        stat.round_two = True
                        db.session.add(stat)
                    m+=1
                    n-=1
                print("Round 2 matches created!")
                db.session.commit()
                return redirect(url_for('views.teams'))

            # Check to see if all of playoffs round_two series have been played
            playoffsRoundTwoIsComplete = all(series.winningTeam is not None for series in roundTwoSeries)

            # Check to see if round_three has already been generated
            roundThreeQuery = text(f'''
                SELECT DISTINCT Team0_id, Team1_id, winningTeam 
                    FROM Stats 
                    WHERE League_id = {current_league_id} AND round_three = 1
                    GROUP BY Team0_id, Team1_id;
            ''')
            with db.engine.connect() as conn:
                roundThreeSeries = conn.execute(roundThreeQuery).fetchall()

            if playoffsRoundTwoIsComplete and not roundThreeSeries:

                # Get the latest Series.id
                last_series_id = db.session.query(func.coalesce(func.max(Series.id), 0)).scalar()

                # Count the number of wins each Team.id appears in Stats.winningTeam with the matching League.id and round_two = True
                results = db.session.query(
                    Stats.winningTeam, Stats.Series_id, func.count()
                ).filter(
                    Stats.League_id == current_league_id,
                    Stats.winningTeam.isnot(None),
                    Stats.round_two == 1
                ).group_by(
                    Stats.winningTeam, Stats.Series_id
                ).having(
                    func.count(Stats.winningTeam) == 2
                ).order_by(
                    Stats.Series_id.asc()
                ).all()

                # Create matches in Stats table for each round_three matchup
                for i in range(1,2):
                    series = Series()
                    series.id = last_series_id + i
                    db.session.add(series)
                    for j in range(1,4):
                        stat = Stats()
                        stat.League_id = current_league_id
                        stat.Series_id = series.id
                        stat.Team0_id = results[0][0]
                        stat.Team1_id = results[1][0]
                        stat.round_three = True
                        db.session.add(stat)
                print("Round 3 matches created!")
                db.session.commit()
                return redirect(url_for('views.teams'))

            else:
                flash("Results submitted!", category="success")
                return redirect(url_for('views.teams'))

# Image upload
@logic.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        profile_image = request.files['profile_image'].read()
        current_user.profile_image = profile_image
        db.session.commit()
    
        return redirect(url_for('views.profile'))