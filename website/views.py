from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import User, Team, TeamPlayers, League, Stats, Series, UserStats
from . import db, images
from sqlalchemy import text, exists, func
from collections import Counter
import os
from urllib.parse import quote

views = Blueprint('views', __name__)

# Home page for root
@views.route('/')
#@login_required
def home():
    return render_template('index.html', user=current_user)

@views.route('/faq')
#@login_required
def faq():
    return render_template('faq.html', user=current_user)

@views.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST' and 'profile_image' in request.files:
        # Get the file to check it's size
        file = request.files['profile_image']

        # Move the file pointer to the end
        file.seek(0, os.SEEK_END)

        # Get the current position of the file pointer, which represents the file size
        file_size = file.tell()

        # Reset the file pointer to the beginning
        file.seek(0)

        if file_size > 0:
            # Set max file size in bytes
            max_size = 2 * 1024 * 1024  # 2MB

            if file_size > max_size:         
                flash("File size cannot exceed 2MB!", category="error")
                return render_template('profile.html' , user=current_user)
            else:
                # Save the image file
                filename = images.save(request.files['profile_image'])

                # Update current_user.profile_image
                current_user.profile_image = filename
                db.session.commit()
            flash("Profile_image saved successfully.", category="success")
            return render_template('profile.html' , user=current_user)
    return render_template('profile.html', user=current_user)

@views.route('/teams')
def teams():
    #Find all usernames from each teamId associated with the current_user.id's teamId's (that's a mouthful)
    query = text(f'''
        SELECT u.username, u.profile_image, t.teamName, t.id, t.teamCaptain, t.team_logo, t.team_banner
        FROM User u
        INNER JOIN TeamPlayers tp ON u.id = tp.userId
        INNER JOIN Team t ON tp.teamId = t.id
        WHERE tp.teamId IN (
            SELECT tp2.teamId
            FROM TeamPlayers tp2
            WHERE tp2.userId = {current_user.id}
        );
    ''')
    with db.engine.connect() as con:
        result = con.execute(query)
        teams = result.fetchall()
        
        # Store the results in a nested dictionary to make it easier to access with Jinja
        team_users = {}
        for team in teams:
            team_id = team[3]
            if team_id not in team_users:
                team_users[team_id] = {
                    'team_name': team[2],
                    'team_captain': team[4],
                    'team_logo': team[5],
                    'team_banner': team[6],
                    'users': []
                }
            team_users[team_id]['users'].append({
                'username': team[0],
                'profile_image': team[1]
            })

    # Pass team.id, team.teamName and their associated user.usernames to be rendered
    return render_template('teams.html', user=current_user, teams=team_users)

@views.route('/team')
def team():
    # Get current Team.id passed through args
    team_id = request.args.get('team_id')
    # Get team object with matching Team.id passed through args
    team = Team.query.filter(Team.id == team_id).first()
    # Get the players for the team
    players = User.query.join(TeamPlayers).join(Team).filter(Team.id == team_id).all()
    # Get the League object associated with the current_team
    league = League.query.filter(League.team_id == team.id, League.isActive == True).first()

    # Check if team isActive, if not render joinQueue button and numberInQueue
    if league is None:
        query = text(f'''
            SELECT t.id, t.rank, t.region, t.isQueued
            FROM Team t
            WHERE t.isQueued = 1
        ''')
        with db.engine.connect() as conn:
            teamsList = conn.execute(query).fetchall()
        # Filter out teams that don't match current teams rank and region
        filteredTeams = [t for t in teamsList if ((t.rank == team.rank) and (t.region == team.region) and (t.isQueued))]
        numberInQueue = len(filteredTeams)

        # Render the team page template and pass in the team and players objects
        return render_template('team.html', user=current_user, current_team=team, numberInQueue=numberInQueue, current_league=league, players=players)
    if league.isPlayoffs == 0:

        # Get all season matchups from Stats table associated with the League.id and Team.id
        matchupQuery = text(f'''
            SELECT DISTINCT s.Series_id, s.Team0_id, s.Team1_id, t1.teamName AS Team0_name, t2.teamName AS Team1_name
                FROM Stats s 
                JOIN Team t1 ON s.Team0_id = t1.id 
                JOIN Team t2 ON s.Team1_id = t2.id 
                WHERE s.League_id = {league.id} AND round_one = 0 AND round_two = 0 and round_three = 0 AND (s.Team0_id = {team.id} OR s.Team1_id = {team.id});
        ''')

        with db.engine.connect() as conn:
            matchList = conn.execute(matchupQuery).fetchall()

        # Get the Series_id's from the above query
        series_ids = [row[0] for row in matchList]

        statsQuery = text(f'''
            SELECT UserStats.User_id,
                    ROUND(AVG(UserStats.score), 1) AS avg_score,
                    ROUND(AVG(UserStats.goals), 1) AS avg_goals,
                    ROUND(AVG(UserStats.assists), 1) AS avg_assists,
                    ROUND(AVG(UserStats.saves), 1) AS avg_saves,
                    ROUND(AVG(UserStats.shots), 1) AS avg_shots
                FROM UserStats
                INNER JOIN TeamPlayers ON UserStats.User_id = TeamPlayers.userId
                WHERE TeamPlayers.teamId = :team_id
                AND UserStats.Series_id IN :series_ids
                GROUP BY UserStats.User_id;
        ''')

        with db.engine.connect() as conn:
            statsList = conn.execute(statsQuery, team_id=team_id, series_ids=series_ids).fetchall()

        print(statsList[0])

        matchups = {}
        for row in matchList:
            series_id = row[0]  # Use integer index instead of string index
            matchups[series_id] = {
                "Team0_id": row[1],
                "Team0_name": row[3],
                "Team1_id": row[2],
                "Team1_name": row[4],
            }

        return render_template('team.html', user=current_user, current_team=team, current_league=league, matchups=matchups, players=players)

    if league.isPlayoffs:

        # Get highest Series_id from Stats
        seriesQuery = text(f'''
            SELECT * from Stats
            WHERE League_id = {league.id} AND
            (Team0_id = {team_id} or Team1_id = {team_id})
            ORDER BY Series_id DESC
        ''')
        with db.engine.connect() as conn:
            activeSeries = conn.execute(seriesQuery).first()

        if activeSeries.round_one:

            # Get round_one playoff matchup
            query = text(f'''
                SELECT DISTINCT s.Series_id, s.Team0_id, s.Team1_id, t1.teamName AS Team0_name, t2.teamName AS Team1_name, winningTeam
                    FROM Stats s 
                    JOIN Team t1 ON s.Team0_id = t1.id 
                    JOIN Team t2 ON s.Team1_id = t2.id 
                    WHERE s.League_id = {league.id} AND round_one = 1 AND (s.Team0_id = {team.id} OR s.Team1_id = {team.id});
            ''')
            with db.engine.connect() as conn:
                playoffSeries = conn.execute(query).first()

            round_name = "Quarter-Finals"

            return render_template('team.html', user=current_user, current_team=team, current_league=league, playoffSeries=playoffSeries, round_name=round_name, players=players)
        
        if activeSeries.round_two:

            # Get round_one playoff matchup
            query = text(f'''
                SELECT DISTINCT s.Series_id, s.Team0_id, s.Team1_id, t1.teamName AS Team0_name, t2.teamName AS Team1_name, winningTeam
                    FROM Stats s 
                    JOIN Team t1 ON s.Team0_id = t1.id 
                    JOIN Team t2 ON s.Team1_id = t2.id 
                    WHERE s.League_id = {league.id} AND round_two = 1 AND (s.Team0_id = {team.id} OR s.Team1_id = {team.id});
            ''')
            with db.engine.connect() as conn:
                playoffSeries = conn.execute(query).first()

            round_name = "Semi-Finals"

            return render_template('team.html', user=current_user, current_team=team, current_league=league, playoffSeries=playoffSeries, round_name=round_name, players=players)
        
        if activeSeries.round_three:

            # Get round_one playoff matchup
            query = text(f'''
                SELECT DISTINCT s.Series_id, s.Team0_id, s.Team1_id, t1.teamName AS Team0_name, t2.teamName AS Team1_name, winningTeam
                    FROM Stats s 
                    JOIN Team t1 ON s.Team0_id = t1.id 
                    JOIN Team t2 ON s.Team1_id = t2.id 
                    WHERE s.League_id = {league.id} AND round_three = 1 AND (s.Team0_id = {team.id} OR s.Team1_id = {team.id});
            ''')
            with db.engine.connect() as conn:
                playoffSeries = conn.execute(query).first()

            round_name = "Championship"

            return render_template('team.html', user=current_user, current_team=team, current_league=league, playoffSeries=playoffSeries, round_name=round_name, players=players)


@views.route('/match') #TODO: Get usernames, use profile image, team logo and team banner to pass to template
def match():
    # Get both Team.id's and League.id from args for current matchup
    current_league_id = request.args.get('current_league')
    team0_id = request.args.get('team0_id')
    team1_id = request.args.get('team1_id')
    series_id = request.args.get('series_id')

    # Get Team object for each Team
    team0 = Team.query.filter(Team.id == team0_id).first()
    team1 = Team.query.filter(Team.id == team1_id).first()

    # Check to see if scores have already been submitted
    query = text(f'''
        SELECT * FROM Stats 
			WHERE League_id = {current_league_id} AND 
			Series_id = {series_id}
    ''')

    with db.engine.connect() as conn:
        series = conn.execute(query).fetchall()
    
    hasWinner = False
    for row in series:
        if row.winningTeam is not None:
            hasWinner = True
            break

    return render_template('match.html', user=current_user, team0=team0, team1=team1, current_league_id=current_league_id, hasWinner=hasWinner, series_id=series_id)

@views.route('/bracket')
def bracket():

    # Get League.id from args
    current_league_id = request.args.get('league_id')

    # Get count of winningTeam and their respective Team.teamName to fill bracket
    seasonQuery = text(f'''
        SELECT Stats.winningTeam, COUNT(*), Team.teamName
            FROM Stats
            JOIN Team ON Stats.winningTeam = Team.id
            WHERE Stats.League_id = {current_league_id} AND Stats.winningTeam IS NOT NULL AND round_one = 0 AND round_two = 0 AND round_three = 0
            GROUP BY Stats.winningTeam
            ORDER BY COUNT(*) DESC
        ''')
    with db.engine.connect() as conn:
        results = conn.execute(seasonQuery).fetchall()

    # Check to see if round_one matches have been played
    roundOneQuery = text(f'''
        SELECT DISTINCT s.Series_id, 
            COALESCE((SELECT winningTeam 
                        FROM Stats 
                        WHERE League_id = {current_league_id} 
                        AND round_one = 1 
                        AND Series_id = s.Series_id 
                        GROUP BY winningTeam 
                        ORDER BY COUNT(winningTeam) DESC 
                        LIMIT 1), '') as most_winningTeam,
            COALESCE(Team.teamName, '') as teamName
        FROM Stats s
        LEFT JOIN Team ON Team.id = COALESCE((SELECT winningTeam 
                                            FROM Stats 
                                            WHERE League_id = {current_league_id} 
                                            AND round_one = 1 
                                            AND Series_id = s.Series_id 
                                            GROUP BY winningTeam 
                                            ORDER BY COUNT(winningTeam) DESC 
                                            LIMIT 1), '')
        WHERE s.League_id = {current_league_id} 
        AND s.round_one = 1
        GROUP BY s.Series_id, Team.teamName
        ORDER BY s.Series_id ASC;
        ''')
    with db.engine.connect() as conn:
        roundOneResults = conn.execute(roundOneQuery).fetchall()

    # Add roundOneResults to the existing results list
    results.extend(roundOneResults)

    # Check to see if round_two matches have been played
    roundTwoQuery = text(f'''
        SELECT DISTINCT s.Series_id, 
            COALESCE((SELECT winningTeam 
                        FROM Stats 
                        WHERE League_id = {current_league_id} 
                        AND round_two = 1 
                        AND Series_id = s.Series_id 
                        GROUP BY winningTeam 
                        ORDER BY COUNT(winningTeam) DESC 
                        LIMIT 1), '') as most_winningTeam,
            COALESCE(Team.teamName, '') as teamName
        FROM Stats s
        LEFT JOIN Team ON Team.id = COALESCE((SELECT winningTeam 
                                            FROM Stats 
                                            WHERE League_id = {current_league_id} 
                                            AND round_two = 1 
                                            AND Series_id = s.Series_id 
                                            GROUP BY winningTeam 
                                            ORDER BY COUNT(winningTeam) DESC 
                                            LIMIT 1), '')
        WHERE s.League_id = {current_league_id} 
        AND s.round_two = 1
        GROUP BY s.Series_id, Team.teamName
        ORDER BY s.Series_id ASC;
        ''')
    with db.engine.connect() as conn:
        roundTwoResults = conn.execute(roundTwoQuery).fetchall()

    if roundTwoResults:

        # Add roundOneResults to the existing results list
        results.extend(roundTwoResults)

    if not roundTwoResults:
        empty_list = [" , , ", " , , ", " , ,"]
        results.extend(empty_list)

    # Check to see if round_three matches have been played
    roundThreeQuery = text(f'''
        SELECT DISTINCT s.Series_id, 
            COALESCE((SELECT winningTeam 
                        FROM Stats 
                        WHERE League_id = {current_league_id} 
                        AND round_three = 1 
                        AND Series_id = s.Series_id 
                        GROUP BY winningTeam 
                        ORDER BY COUNT(winningTeam) DESC 
                        LIMIT 1), '') as most_winningTeam,
            COALESCE(Team.teamName, '') as teamName
        FROM Stats s
        LEFT JOIN Team ON Team.id = COALESCE((SELECT winningTeam 
                                            FROM Stats 
                                            WHERE League_id = {current_league_id} 
                                            AND round_three = 1 
                                            AND Series_id = s.Series_id 
                                            GROUP BY winningTeam 
                                            ORDER BY COUNT(winningTeam) DESC 
                                            LIMIT 1), '')
        WHERE s.League_id = {current_league_id} 
        AND s.round_three = 1
        GROUP BY s.Series_id, Team.teamName
        ORDER BY s.Series_id ASC;
        ''')
    with db.engine.connect() as conn:
        roundThreeResults = conn.execute(roundThreeQuery).fetchall()

    if roundThreeResults:

        # Add roundOneResults to the existing results list
        results.extend(roundThreeResults)

    if not roundThreeResults:
        empty_list = [" , , "]
        results.extend(empty_list)

    return render_template('bracket.html', user=current_user, results=results)

@views.route('/submitScore')
def submitScore():
    # Get League.id and Team.teamNames from args
    current_league_id = request.args.get('current_league_id')
    current_team = request.args.get('current_team')
    opponent_team = request.args.get('opponent_team')
    series_id = request.args.get('series_id')

    # Get Team from db with matching teamNames
    current_team = Team.query.filter_by(id=current_team).first()
    opponent_team = Team.query.filter_by(id=opponent_team).first()

    # # Get Users associated with Team.Id's from TeamPlayes
    current_team_users = User.query.join(TeamPlayers).filter_by(teamId=current_team.id).all()
    opponent_team_users = User.query.join(TeamPlayers).filter_by(teamId=opponent_team.id).all()

    # # Store Team.id with Users object inside
    current_team_dict = {'teamId': current_team.id, 'users': current_team_users}
    opponent_team_dict = {'teamId': opponent_team.id, 'users': opponent_team_users}

    return render_template('submitScore.html',
                                user=current_user,
                                current_team_name=current_team.teamName,
                                opponent_team_name=opponent_team.teamName,
                                current_team_dict=current_team_dict,
                                opponent_team_dict=opponent_team_dict,
                                current_league_id=current_league_id,
                                series_id=series_id
                            )

@views.route('/league')
def league():
    return render_template('league.html', user=current_user)

@views.route('/createTeam')
def createTeam():
    return render_template('createTeam.html', user=current_user)

@views.route('/joinQueue')
def joinQueue():
    # Get current Team.id passed through args
    team_id = request.args.get('current_team')

    # Get team object with matching Team.id passed through args
    team = Team.query.filter(Team.id == team_id).first()

    # Get all teams in the queue
    queued_teams = Team.query.filter_by(rank=team.rank, region=team.region, isQueued=True).all()
    queued_team_ids = [t.id for t in queued_teams]

    # Get a list of User.id's associated with the Team.ids in the queue
    queued_user_ids = TeamPlayers.query.filter(TeamPlayers.teamId.in_(queued_team_ids)).values(TeamPlayers.userId)
    queued_user_ids = [u[0] for u in queued_user_ids]

    current_team = TeamPlayers.query.filter(TeamPlayers.teamId == team_id).all()
    current_team_ids = [u.userId for u in current_team]

    # Create set's so they can be cross checked
    queued_user_ids_set = set(queued_user_ids)
    current_team_ids_set = set(current_team_ids)

    # Check to see if user who clicked joinQueue is a captain
    if current_user.id != team.teamCaptain:
        flash("Only the captain of the team can join the queue.", category="error")
        return redirect(url_for('views.team', team_id=team_id))
    # Crosscheck User.ids associated with Team.ids already in queue to see if User.id's from the current team already exist in the queue    
    if current_team_ids_set.intersection(queued_user_ids_set):
        flash(f"You or your teammate are on a different team in the current queue.", category="error")
        return redirect(url_for('views.team', team_id=team_id))
    # If not change isQueued = true
    if team:
        team.isQueued = True
        db.session.commit()

        # Count number of teams in queue for current team's rank/region
        count = Team.query.filter_by(rank=team.rank, region=team.region, isQueued=True).count()
        flash(f"{team.teamName} has been added to the queue. Position:{count}/8", category="success")

        # Queue is full, add teams to league
        if count == 8:

            # Get all teams in the queue
            queued_teams = Team.query.filter_by(rank=team.rank, region=team.region, isQueued=True).all()
            
            # Set isQueued = False 
            for t in queued_teams:
                t.isQueued = False

            # Get the latest League.id
            last_league_id = db.session.query(func.coalesce(func.max(League.id), 0)).scalar()

            # Increment the League.id by 1
            new_league_id = last_league_id + 1
            
            # Create League entries
            league_entries = [League(id=new_league_id, team_id=t.id, isActive=True) for t in queued_teams]

            # Get the latest Series.id
            last_series_id = db.session.query(func.coalesce(func.max(Series.id), 0)).scalar()

            # Create n!/(n-p)!p! new series entries. for [1, 2, 3, 4, 5, 6, 7, 8] -> 28 entries.
            checkpoints = [7, 13, 18, 22, 25, 27, 28]
            m = 0
            n = 1
            x = 1
            for i in range(1, 29):
                series = Series()
                series.id = last_series_id + i
                db.session.add(series)
                for j in range(1, 4):
                    stat = Stats()
                    stat.League_id = new_league_id
                    stat.Series_id = series.id
                    stat.Team0_id = queued_teams[m].id
                    stat.Team1_id = queued_teams[n].id
                    db.session.add(stat)
                n+=1
                if i in checkpoints:
                    m+= 1
                    n = 1 + x
                    x+= 1

            # Commit changes to the database
            db.session.add_all(league_entries)
            db.session.commit()
                    
            flash("Queue is now full and bracket has been generated!", category="success")

    else:
        # Handle the case where no matching team is found
        flash("Unable to find the specified team.", category="error")

    return redirect(url_for('views.team', team_id=team_id))

@views.route('/leaveQueue')
def leaveQueue():
    # Get current Team.id passed through args
    team_id = request.args.get('current_team')

    # Get team object with matching Team.id passed through args
    team = Team.query.filter(Team.id == team_id).first()

    # Set isQueued to false to remove team from queue
    team.isQueued = 0 

    db.session.commit()

    flash("Your team has been removed from the queue.", category="success")
    return redirect(url_for('views.team', team_id=team_id))

@views.route('/editTeam', methods=['GET', 'POST'])
#@login_required
def editTeam():
    # Get Team.id from args to pass back to template
    team_id = request.args.get('team_id')

    if request.method == 'POST':
        # Set max file size in bytes
        max_size = 2 * 1024 * 1024  # 2MB

        # Check if team logo is uploaded
        if 'team_logo' in request.files:
            # Get the file to check it's size
            logo_file = request.files['team_logo']

            # Move the file pointer to the end
            logo_file.seek(0, os.SEEK_END)

            # Get the current position of the file pointer, which represents the file size
            logo_size = logo_file.tell()

            # Reset the file pointer to the beginning
            logo_file.seek(0)

            if logo_size > 0:
                if logo_size > max_size:         
                    flash("File size cannot exceed 2MB!", category="error")
                    return render_template('editTeam.html', user=current_user)
                else:
                    # Get Team.id from form
                    team_id = request.form['team_id']

                    # Get team object with matching Team.id passed through args
                    team = Team.query.filter(Team.id == team_id).first()

                    # Save the image file
                    filename = images.save(request.files['team_logo'])

                    # Update team.team_logo
                    team.team_logo = filename
                    db.session.commit()
                flash("Team logo saved successfully.", category="success")
                return redirect(url_for('views.teams'))
        # Check if team banner is uploaded
        if 'team_banner' in request.files:
            # Get the file to check it's size
            banner_file = request.files['team_banner']

            # Move the file pointer to the end
            banner_file.seek(0, os.SEEK_END)

            # Get the current position of the file pointer, which represents the file size
            banner_size = banner_file.tell()

            # Reset the file pointer to the beginning
            banner_file.seek(0)

            if banner_size > 0:
                if banner_size > max_size:         
                    flash("File size cannot exceed 2MB!", category="error")
                    return render_template('editTeam.html', user=current_user)
                else:
                    # Get Team.id from form
                    team_id = request.form['team_id']

                    # Get team object with matching Team.id passed through args
                    team = Team.query.filter(Team.id == team_id).first()

                    # Save the image file
                    filename = images.save(request.files['team_banner'])

                    # Update team.team_banner
                    team.team_banner = filename
                    db.session.commit()
                flash("Team banner saved successfully.", category="success")
                return redirect(url_for('views.teams'))
    return render_template('editTeam.html', user=current_user, team_id=team_id)