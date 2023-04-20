from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import User, Team, TeamPlayers, League, Stats, Series
from . import db
from sqlalchemy import text, func
from collections import Counter

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
    #Find all usernames from each teamId associated with the current_user.id's teamId's (that's a mouthful)
    query = text(f'''
        SELECT u.username, t.teamName, t.id
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
            team_name = team[1]
            team_id = team[2]
            if team_id not in team_users:
                team_users[team_id] = (team_name, [])
            team_users[team_id][1].append(team[0])

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
    # Get a list of usernames for the players
    usernames = [player.username for player in players]
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
        return render_template('team.html', user=current_user, current_team=team, usernames=usernames, numberInQueue=numberInQueue, current_league=league)
    if league.isPlayoffs == 0:

        # Get all seasone matchups from Stats table associated with the League.id and Team.id
        query = text(f'''
            SELECT DISTINCT s.Series_id, s.Team0_id, s.Team1_id, t1.teamName AS Team0_name, t2.teamName AS Team1_name
                FROM Stats s 
                JOIN Team t1 ON s.Team0_id = t1.id 
                JOIN Team t2 ON s.Team1_id = t2.id 
                WHERE s.League_id = {league.id} AND round_one = 0 AND round_two = 0 and round_three = 0 AND (s.Team0_id = {team.id} OR s.Team1_id = {team.id});
        ''').columns(Stats.Series_id, Stats.Team0_id, Stats.Team1_id)

        with db.engine.connect() as conn:
            teamsList = conn.execute(query).fetchall()

        matchups = {}
        for row in teamsList:
            series_id = row["Series_id"]
            matchups[series_id] = {
                "Team0_id": row["Team0_id"],
                "Team0_name": row["Team0_name"],
                "Team1_id": row["Team1_id"],
                "Team1_name": row["Team1_name"],
            }

            return render_template('team.html', user=current_user, current_team=team, usernames=usernames, current_league=league, matchups=matchups)

    if league.isPlayoffs:

        # Get highest Series_id from Stats
        seriesQuery = text(f'''
            SELECT * from Stats
            WHERE League_id = 20 AND
            (Team0_id = 1 or Team1_id = 1)
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

            return render_template('team.html', user=current_user, current_team=team, usernames=usernames, current_league=league, playoffSeries=playoffSeries, round_name=round_name)
        
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

            return render_template('team.html', user=current_user, current_team=team, usernames=usernames, current_league=league, playoffSeries=playoffSeries, round_name=round_name)
        
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

            return render_template('team.html', user=current_user, current_team=team, usernames=usernames, current_league=league, playoffSeries=playoffSeries, round_name=round_name)


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
    
    # Check to see if scores have already been submitted
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
        SELECT Stats.winningTeam, COUNT(*), Team.teamName
            FROM Stats
            JOIN Team ON Stats.winningTeam = Team.id
            WHERE Stats.League_id = 19
            AND round_one = 1 AND round_two = 0 AND round_three = 0
            GROUP BY Stats.winningTeam, Team.teamName
            HAVING COUNT(*) = 2;
        ''')
    with db.engine.connect() as conn:
        roundOneResults = conn.execute(roundOneQuery).fetchall()

    

    return render_template('bracket.html', user=current_user, results=results)

@views.route('/submitScore')
def submitScore():
    # Get League.id and Team.teamNames from args
    current_league_id = request.args.get('current_league_id')
    current_team_name = request.args.get('current_team')
    opponent_team_name = request.args.get('opponent_team')
    series_id = request.args.get('series_id')

    # Get Team from db with matching teamNames
    current_team = Team.query.filter_by(teamName=current_team_name).first()
    opponent_team = Team.query.filter_by(teamName=opponent_team_name).first()

    # # Get Users associated with Team.Id's from TeamPlayes
    current_team_users = User.query.join(TeamPlayers).filter_by(teamId=current_team.id).all()
    opponent_team_users = User.query.join(TeamPlayers).filter_by(teamId=opponent_team.id).all()

    # # Store Team.id with User.usernames inside
    current_team_dict = {'teamId': current_team.id, 'usernames': [user.username for user in current_team_users]}
    opponent_team_dict = {'teamId': opponent_team.id, 'usernames': [user.username for user in opponent_team_users]}

    return render_template('submitScore.html',
                                user=current_user,
                                current_team_name=current_team_name,
                                opponent_team_name=opponent_team_name,
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
    print(team_id)
    # Get team object with matching Team.id passed through args
    team = Team.query.filter(Team.id == team_id).first()
    print(team)
    # Get the League object associated with the current_team
    league = League.query.filter(League.team_id == team.id, League.isActive == True).first()

    # Check to see if user who clicked joinQueue is a captain
    if current_user.id != team.teamCaptain:
        flash("Only the captain of the team can join the queue.", category="error")
        return redirect(url_for('views.teams'))
    # Check to see if team is already in a league with the same rank/region combination    
    if team and team.isQueued or league: # this is slightly unclear --thomas
        flash(f"{team.teamName} is already queued or active in this rank and region.", category="error")
        return redirect(url_for('views.teams'))
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

    return redirect(url_for('views.teams'))
