from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User, Team, TeamPlayers, Stats, Series, League, UserStats
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
        userOne = User.query.filter_by(id=userOneIdForm).first()

        # Make sure no fields are blank
        if not teamName or not userOneNameForm or not userOneIdForm:
            flash('Please fill out all the fields.', category='error')
            return render_template('createTeam.html', user=current_user)

        # Make sure both users have a rank
        if current_user.rank == None or userOne.rank == None:
            flash('You or your teammate have not been assigned a rank yet.', category='error')
            flash('Please wait 24 hours, if this error persists contact support on our discord.', category='error')
            return render_template('createTeam.html', user=current_user)

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
            #Validate the two users don't already have a team together
            existingTeam = db.session.query(TeamPlayers.teamId).filter(TeamPlayers.userId.in_([captainID, userOne.id])).group_by(TeamPlayers.teamId).having(func.count(TeamPlayers.teamId) == 2).scalar()
            if existingTeam is not None:
                flash('You cannot have two teams with the same teammate.', category='error')
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
        # Get current Team.id, League.id, Series_id from form
        team_id = request.form.get('team_id')
        current_league_id = request.form['current_league_id']
        series_id = request.form['series_id']
        print(current_league_id, series_id, team_id)

        # Get current Series object
        current_series = Stats.query.filter_by(Series_id=series_id).first()

        # Get both Team.id's associated with the current series
        team0 = current_series.Team0_id
        team1 = current_series.Team1_id
        print("Team0:", team0)
        print("Team1:", team1)

        # Get game winners Team.id's from form
        winners = [int(request.form.get('gameOneWinner')), int(request.form.get('gameTwoWinner')), int(request.form.get('gameThreeWinner'))]
        print(winners)

        # Create a list of Team.id's for each game loss being the opposite of the values in winners
        losers = []
        for winner in winners:
            if winner == team0:
                losers.append(team1)
            elif winner == team1:
                losers.append(team0)

        print(losers)

        # Check to see if score have already been submitted
        if current_series.winningTeam is not None:
            flash("Scores have already been submitted for this match.", category="error")
            return redirect(request.referrer)

        # Check to make sure that all three values are not the same
        if len(set(winners)) == 1:
            flash("One team cannot win all 3 games in a best of 3, please try again.", category="error")
            return redirect(request.referrer)

        # Check to see if a tie was submitted
        if winners[0] != winners[1] and winners[2] == 0:
            flash("You submitted a tie.", category="error")
            return redirect(request.referrer)
        
        # Check if game 3 has a winner for no reason
        if winners[0] == winners[1] and winners[2] != 0:
            flash("Game 3 cannot have a winner if the series is over after two games.", category="error")
            return redirect(request.referrer)

        # Get the series winner
        winnerCount = Counter(winners)
        seriesWinner = winnerCount.most_common(1)[0][0]

        # Determine the series loser
        seriesLoser = current_series.Team0_id if current_series.Team1_id == seriesWinner else current_series.Team1_id

        print(winnerCount, seriesWinner, seriesLoser)

        # WHERE clause for update queries
        where_clause = Stats.Series_id == series_id

        # Check if there are exactly 2 or 3 winners
        if len(winners) in [2, 3]:
            #Define # of users based on # of games played
            num_users = 8 if len([x for x in winners if x != 0]) == 2 else 12
            print(num_users)

            # Check to make sure players are not duplicated per game
            gameOne = [int(request.form.get('user1')), int(request.form.get('user2')), int(request.form.get('user3')), int(request.form.get('user4'))]
            gameTwo = [int(request.form.get('user5')), int(request.form.get('user6')), int(request.form.get('user7')), int(request.form.get('user8'))]
            
            if len(gameOne) != len(set(gameOne)) or len(gameTwo) != len(set(gameTwo)):
                flash("One user has been selected for two stat lines, please correct this error.", category="error")
                return redirect(request.referrer)   
            
            if num_users == 12:
                gameThree = [int(request.form.get('user9')), int(request.form.get('user10')), int(request.form.get('user11')), int(request.form.get('user12'))]
                if len(gameThree) != len(set(gameThree)):
                    flash("One user has been selected for two stat lines, please correct this error.", category="error")
                    return redirect(request.referrer)

            # Get data for each user from form
            for i in range(num_users + 1):
                user_id_key = f'user{i}'
                user_score_key = f'user{i}Score'
                user_goals_key = f'user{i}Goals'
                user_saves_key = f'user{i}Saves'
                user_assists_key = f'user{i}Assists'
                user_shots_key = f'user{i}Shots'

                if (
                    user_id_key not in request.form or
                    user_score_key not in request.form or
                    user_goals_key not in request.form or
                    user_saves_key not in request.form or
                    user_assists_key not in request.form or
                    user_shots_key not in request.form
                ):
                    continue

                user_id = int(request.form.get(user_id_key))
                score = int(request.form.get(user_score_key))
                goals = int(request.form.get(user_goals_key))
                saves = int(request.form.get(user_saves_key))
                assists = int(request.form.get(user_assists_key))
                shots = int(request.form.get(user_shots_key))

                # Create object to pass to db
                user_stats = UserStats(
                    Series_id=series_id,
                    User_id=user_id,
                    score=score,
                    goals=goals,
                    saves=saves,
                    assists=assists,
                    shots=shots
                )

                # Add the user stats to the database session
                db.session.add(user_stats)

            # Get the rows to update
            stats_to_update = db.session.query(Stats).filter(where_clause).limit(len(winners)).all()

            # Update winningTeam for each row
            for i, stat in enumerate(stats_to_update):
                if winners[i] != 0:
                    stat.winningTeam = winners[i]
                    stat.losingTeam = losers[i]

            # Get Series to update
            series = Series.query.filter(Series.id == stats_to_update[0].Series_id).first()

            # Update Series table
            series.seriesWinner = seriesWinner
            series.seriesLoser = seriesLoser

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
            
            print("Season check:", seasonIsComplete, roundOneSeries)
            if seasonIsComplete and not roundOneSeries:

                # Query to get Teams and their wins/losses by League.id
                standingsQuery = text(f'''
                    SELECT * FROM (
                    SELECT ROW_NUMBER() OVER (ORDER BY subquery.wins DESC, subquery3.gameWins DESC) AS place,
                        l.team_id, t.teamName,
                        COALESCE(subquery.wins, 0) AS seriesWins,
                        COALESCE(subquery3.gameWins, 0) AS gameWins,
                        COALESCE(subquery2.losses, 0) AS seriesLosses,
                        COALESCE(subquery4.gameLosses, 0) AS gameLosses,
                        t.team_logo, t.team_banner
                    FROM League l
                    LEFT JOIN (
                        SELECT s.seriesWinner, COUNT(s.seriesWinner) AS wins
                        FROM Series s
                        WHERE s.id IN (SELECT Series_id FROM Stats WHERE League_id = {current_league_id} AND round_one = 0 AND round_two = 0 AND round_three = 0)
                        GROUP BY s.seriesWinner
                    ) AS subquery ON l.team_id = subquery.seriesWinner
                    LEFT JOIN (
                        SELECT s.seriesLoser, COUNT(s.seriesLoser) AS losses
                        FROM Series s
                        WHERE s.id IN (SELECT Series_id FROM Stats WHERE League_id = {current_league_id} AND round_one = 0 AND round_two = 0 AND round_three = 0)
                        GROUP BY s.seriesLoser
                    ) AS subquery2 ON l.team_id = subquery2.seriesLoser
                    LEFT JOIN (
                        SELECT s.winningTeam, COUNT(s.winningTeam) AS gameWins
                        FROM Stats s
                        WHERE s.League_id = {current_league_id} AND round_one = 0 AND round_two = 0 AND round_three = 0
                        GROUP BY s.winningTeam
                    ) AS subquery3 ON l.team_id = subquery3.winningTeam
                    LEFT JOIN (
                        SELECT s.losingTeam, COUNT(s.losingTeam) AS gameLosses
                        FROM Stats s
                        WHERE s.League_id = {current_league_id} AND round_one = 0 AND round_two = 0 AND round_three = 0
                        GROUP BY s.losingTeam
                    ) AS subquery4 ON l.team_id = subquery4.losingTeam
                    JOIN Team t ON l.team_id = t.id
                    WHERE l.id = {current_league_id}
                ) AS subquery5
                ORDER BY place;
                ''')

                with db.engine.connect() as conn:
                    season_results = conn.execute(standingsQuery).fetchall()

                print("-------------STANDINGS------------")
                for team in season_results:
                    print(team)

                # Change isPlayoffs = True for all teams with matching current League.id
                e = 0 
                for f in range(1,7):
                    team_id_list = [team[1] for team in season_results[e:e+1]]
                    db.session.query(League).filter(League.id == current_league_id, League.team_id.in_(team_id_list)).update({"isPlayoffs": True})
                    print("Set isPlayoffs = True", team_id_list)
                    e += 1

                # Remove teams in last two places from the League
                db.session.query(League).filter(League.id == current_league_id, League.team_id.in_([season_results[6][1], season_results[7][1]])).update({"isActive": False})
                print("Set isActive = False", season_results[6][1], season_results[7][1])

                db.session.query(Team).filter(Team.id == season_results[6][1]).update({"message": "Your team ended the season in 7th place and did not qualify for the playoffs. Better luck next time! If you are enjoying The Underground please consider leaving a donation."})
                db.session.query(Team).filter(Team.id == season_results[7][1]).update({"message": "Your team ended the season in 8th place and did not qualify for the playoffs. Better luck next time! If you are enjoying The Underground please consider leaving a donation."})

                # Get the latest Series.id
                last_series_id = db.session.query(func.coalesce(func.max(Series.id), 0)).scalar()

                # Add a series win for seed 1 & 2 to simulate bye week
                b = 0
                for c in range(1,3):
                    bye_series = Series()
                    bye_series.id = last_series_id + c
                    db.session.add(bye_series)
                    for d in range(1,3):
                        bye_stat = Stats()
                        bye_stat.League_id = current_league_id
                        bye_stat.Series_id = bye_series.id
                        bye_stat.Team0_id = season_results[b][1]
                        bye_stat.winningTeam = season_results[b][1]
                        bye_stat.round_one = True
                        db.session.add(bye_stat)
                    b+=1
                db.session.commit()

                # Get the latest Series.id
                last_series_id = db.session.query(func.coalesce(func.max(Series.id), 0)).scalar()

                # Create matches in Stats table for the round_one matchup
                m = 2
                n = 5
                for i in range(1,3):
                    series = Series()
                    series.id = last_series_id + i
                    db.session.add(series)
                    for j in range(1,4):
                        stat = Stats()
                        stat.League_id = current_league_id
                        stat.Series_id = series.id
                        stat.Team0_id = season_results[m][1]
                        stat.Team1_id = season_results[n][1]
                        stat.round_one = True
                        db.session.add(stat)
                    m+=1
                    n-=1
                db.session.commit()

                flash("Results submitted!", category="success")
                return redirect(url_for('views.team', team_id=team_id))
            
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

            print("Round One Check:", roundOneSeries, playoffsRoundOneIsComplete, roundTwoSeries)
            if roundOneSeries and playoffsRoundOneIsComplete and not roundTwoSeries:

                # Get the latest Series.id
                last_series_id = db.session.query(func.coalesce(func.max(Series.id), 0)).scalar()

                # Count the number of wins each Team.id appears in Stats.winningTeam with the matching League.id and round_one = True
                round_one_results = db.session.query(
                    Stats.Series_id, Stats.winningTeam, Stats.losingTeam, func.count()
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

                print("----------Round One Results------------")
                for newTeams in round_one_results:
                    print(newTeams)

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
                        stat.Team0_id = round_one_results[m][1]
                        stat.Team1_id = round_one_results[n][1]
                        stat.round_two = True
                        db.session.add(stat)
                    m+=1
                    n-=1

                # Remove losing teams from League
                db.session.query(League).filter(League.id == current_league_id, League.team_id.in_([round_one_results[2][2], round_one_results[3][2]])).update({"isActive": False, "isPlayoffs": False})
                print("Set isActive = False", round_one_results[2][2], round_one_results[3][2])

                db.session.query(Team).filter(Team.id == round_one_results[2][2]).update({"message": "You have been elimated from the playoffs in the quarter-finals. If you are enjoying The Underground please consider leaving a donation."})
                db.session.query(Team).filter(Team.id == round_one_results[3][2]).update({"message": "You have been elimated from the playoffs in the quarter-finals. If you are enjoying The Underground please consider leaving a donation."})

                db.session.commit()
                flash("Results submitted!", category="success")
                return redirect(url_for('views.team', team_id=team_id))

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

            print("Round Two Check:", roundTwoSeries, playoffsRoundTwoIsComplete, roundThreeSeries)
            if roundTwoSeries and playoffsRoundTwoIsComplete and not roundThreeSeries:

                # Get the latest Series.id
                last_series_id = db.session.query(func.coalesce(func.max(Series.id), 0)).scalar()

                # Count the number of wins each Team.id appears in Stats.winningTeam with the matching League.id and round_two = True
                round_two_results = db.session.query(
                    Stats.Series_id, Stats.winningTeam, Stats.losingTeam, func.count()
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

                print("----------Round Two Results----------")
                for newerTeams in round_two_results:
                    print(newerTeams)

                # Create matches in Stats table for each round_three matchup
                for i in range(1,2):
                    series = Series()
                    series.id = last_series_id + i
                    db.session.add(series)
                    for j in range(1,4):
                        stat = Stats()
                        stat.League_id = current_league_id
                        stat.Series_id = series.id
                        stat.Team0_id = round_two_results[0][1]
                        stat.Team1_id = round_two_results[1][1]
                        stat.round_three = True
                        db.session.add(stat)

                # Remove losing teams from League
                db.session.query(League).filter(League.id == current_league_id, League.team_id.in_([round_two_results[0][2], round_two_results[1][2]])).update({"isActive": False, "isPlayoffs": False})
                print("Set isActive = False", round_two_results[0][2], round_two_results[1][2])

                db.session.query(Team).filter(Team.id == round_two_results[0][2]).update({"message": "You have been elimated from the playoffs in the semi-finals. If you are enjoying The Underground please consider leaving a donation."})
                db.session.query(Team).filter(Team.id == round_two_results[1][2]).update({"message": "You have been elimated from the playoffs in the semi-finals. If you are enjoying The Underground please consider leaving a donation."})
                    
                db.session.commit()
                flash("Results submitted!", category="success")
                return redirect(url_for('views.team', team_id=team_id))

            playoffsComplete = all(series.winningTeam is not None for series in roundThreeSeries)

            print(playoffsComplete)
            if playoffsComplete:
                # Count the number of wins each Team.id appears in Stats.winningTeam with the matching League.id and round_two = True
                round_three_results = db.session.query(
                    Stats.Series_id, Stats.winningTeam, Stats.losingTeam, func.count()
                ).filter(
                    Stats.League_id == current_league_id,
                    Stats.winningTeam.isnot(None),
                    Stats.round_three == 1
                ).group_by(
                    Stats.winningTeam, Stats.Series_id
                ).having(
                    func.count(Stats.winningTeam) == 2
                ).order_by(
                    Stats.Series_id.asc()
                ).all()

                print("----------Round Three Results----------")
                for newestTeams in round_three_results:
                    print(newestTeams)

                # Remove both teams from the League
                db.session.query(League).filter(League.id == current_league_id, League.team_id.in_([round_three_results[0][1], round_three_results[0][2]])).update({"isActive": False, "isPlayoffs": False})
                print("Set isActive = False", round_three_results[0][1], round_three_results[0][2])

                # Set messages
                db.session.query(Team).filter(Team.id == round_three_results[0][1]).update({"message": "Playoffs are complete, your team got 1st place! If you are enjoying The Underground please consider leaving a donation."})
                db.session.query(Team).filter(Team.id == round_three_results[0][2]).update({"message": "Playoffs are complete, your team got 2nd place! If you are enjoying The Underground please consider leaving a donation."})

                db.session.commit()
                flash("Results submitted!", category="success")
                return redirect(url_for('views.team', team_id=team_id))

            else:
                flash("Results submitted!", category="success")
                return redirect(url_for('views.team', team_id=team_id))