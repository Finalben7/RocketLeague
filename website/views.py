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
    else:

        # Get all matchups from Stats table associated with the League.id and Team.id
        query = text(f'''
            SELECT DISTINCT s.Team0_id, s.Team1_id, t1.teamName AS Team0_name, t2.teamName AS Team1_name 
                FROM Stats s 
                JOIN Team t1 ON s.Team0_id = t1.id 
                JOIN Team t2 ON s.Team1_id = t2.id 
                WHERE s.League_id = {league.id} AND (s.Team0_id = {team.id} OR s.Team1_id = {team.id});
        ''').columns(Stats.Team0_id, Stats.Team1_id)
        with db.engine.connect() as conn:
            teamsList = conn.execute(query).fetchall()

        # Create matches from query in dictionary to sent to template
        matchups = {}
        i = 1
        for row in teamsList:
            key = f"Match #{i}"
            matchups[key] = {
                "Team0_id": row["Team0_id"],
                "Team0_name": row["Team0_name"],
                "Team1_id": row["Team1_id"],
                "Team1_name": row["Team1_name"],
            }
            i += 1

    #                 \\\\\OLD CODE BELOW FOR REFERENCE\\\
    # If team isActive get team names for bracket
    # else: #FIXME: Add logic to make this specific to teams within certain leagues
    #     query = text(f'''
    #      SELECT t.id, t.teamName
    #      FROM Team t
    #      WHERE t.isActive = 1
    # ''')
    # with db.engine.connect() as conn:
    #     team_data = conn.execute(query).fetchall()
    # # Store teamNames is a list to remove quotations and parenthesis
    #     team_names = [data[1] for data in team_data]
    #     team_ids = [data[0] for data in team_data]
    # # Pair teamNames together to create matches
    # match1 = {"team0" : team_names[0], "team1" : team_names[1]}
    # match2 = {"team0" : team_names[2], "team1" : team_names[3]}
    # match3 = {"team0" : "TBD", "team1" : "TBD"}
    # # Check to see if any team is a seriesWinner, if yes add them to match 3
    # winners = text(f'''
    #         SELECT s.seriesWinner, t.teamName
    #         FROM Series s
    #         JOIN Team t ON s.seriesWinner = t.id
    #     ''')
    # with db.engine.connect() as conn:
    #     series_winners = conn.execute(winners).fetchall()
    
    # # Filter winners that don't match current team_ids
    # filteredWinners = [s for s in series_winners if s.seriesWinner in team_ids]

    # winner_names = [w[1] for w in filteredWinners]
    
    # winner=''

    # if len(filteredWinners) == 1:
    #     if winner_names[0] in (match1['team0'], match1['team1']):
    #         match3['team0'] = winner_names[0]
    #     else:
    #         match3['team1'] = winner_names[0]

    # if len(filteredWinners) == 2:
    #     if winner_names[0] in (match1['team0'], match1['team1']):
    #         match3['team0'] = winner_names[0]
    #         match3['team1'] = winner_names[1]
    #     else:
    #         match3['team0'] = winner_names[1]
    #         match3['team1'] = winner_names[0]

    # if len(filteredWinners) == 3:
    #     name_counts = Counter(winner_names)
    #     winner = next((name for name, count in name_counts.items() if count > 1), None)
    #     if winner_names[0] in (match1['team0'], match1['team1']):
    #         match3['team0'] = winner_names[0]
    #         match3['team1'] = winner_names[1]
    #     else:
    #         match3['team0'] = winner_names[1]
    #         match3['team1'] = winner_names[0]


    # # Store matches is bracket dictionary
    # bracket = {"match1" : match1, "match2" : match2, "match3" : match3}
    # # Search bracket for current team_name passed through args to find their opponent team name
    # for match_name, match in bracket.items():
    #     # check if the team_name is in the match dictionary values
    #     if team_name in match.values():
    #         # get the key associated with the other team name
    #         other_team_key = [key for key, value in match.items() if value != team_name][0]
    #         # get the other team name from the match dictionary using the key
    #         opponent_team = match[other_team_key]
    #         # return the other team name
    # removed from return statement opponent_team=opponent_team, winner=winner, bracket=bracket
        return render_template('team.html', user=current_user, current_team=team, usernames=usernames, current_league=league, matchups=matchups)

@views.route('/match') #TODO: Get usernames, use profile image, team logo and team banner to pass to template
def match():
    # Get both Team.id's and League.id from args for current matchup
    current_league_id = request.args.get('current_league')
    team0_id = request.args.get('team0_id')
    team1_id = request.args.get('team1_id')

    # Get Team object for each Team
    team0 = Team.query.filter(Team.id == team0_id).first()
    team1 = Team.query.filter(Team.id == team1_id).first()

    # Check to see if scores have already been submitted
    query = text(f'''
        SELECT * FROM Stats 
			WHERE League_id = {current_league_id} AND 
			(Team0_id = {team0_id} OR Team1_id = {team0_id}) AND 
			(Team0_id = {team1_id} OR Team1_id = {team1_id})
    ''')

    with db.engine.connect() as conn:
        series = conn.execute(query).fetchall()
    
    # Check to see if scores have already been submitted
    hasWinner = False
    for row in series:
        if row.winningTeam is not None:
            hasWinner = True
            break

    return render_template('match.html', user=current_user, team0=team0, team1=team1, current_league_id=current_league_id, hasWinner=hasWinner)

@views.route('/bracket')
def bracket():
    print(request.args.get('league_id'))
    # query = text(f'''
    #      SELECT t.teamName
    #      FROM Team t
    #      WHERE t.isActive = 1
    # ''')
    # with db.engine.connect() as conn:
    #     teamsList = conn.execute(query).fetchall()

    return render_template('bracket.html', user=current_user)

@views.route('/submitScore')
def submitScore():
    # Get League.id and Team.teamNames from args
    current_league_id = request.args.get('current_league_id')
    current_team_name = request.args.get('current_team')
    opponent_team_name = request.args.get('opponent_team')

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
                                current_league_id=current_league_id
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

            # Create six new series entries [1, 2, 3, 4]
            m = 0
            n = 1
            for i in range(1, 7):
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
                if i == 3:
                    m+= 1
                    n = 2
                if i == 5:
                    m+= 1
                    n = 3

            # Commit changes to the database
            db.session.add_all(league_entries)
            db.session.commit()

            # Get the IDs of the newly created Series
            # series_ids = list(range(last_series_id + 1, last_series_id + 7))
                    
            flash("Queue is now full and bracket has been generated!", category="success")

    else:
        # Handle the case where no matching team is found
        flash("Unable to find the specified team.", category="error")

    return redirect(url_for('views.teams'))
