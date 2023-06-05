from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from .models import User, Team, TeamPlayers, League, Stats, Series, UserStats
from . import db, images
from sqlalchemy import text, func
import os

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
    # Get the average stats of the current roster for the current league
    playersQuery = text(f'''
            SELECT us.User_id, u.username, round(avg(goals), 1) as goals, round(avg(assists), 1) as assists, round(avg(saves), 1) as saves, sum(goals) as total_goals, sum(saves) as total_saves, count(*) as games_played, u.profile_image
            FROM UserStats us
            JOIN TeamPlayers tp ON us.User_id = tp.userId
            JOIN League l ON tp.teamId = l.team_id
            JOIN (
            SELECT distinct Series_id
            FROM Stats
            WHERE League_id = {league.id}
            GROUP BY Series_id
            ) s ON us.Series_id = s.Series_id
            JOIN User u ON us.User_id = u.id
            WHERE l.id = {league.id} AND us.User_id IN ({", ".join(str(player.id) for player in players)})
            GROUP BY us.User_id, u.username, u.profile_image
        ''')

    with db.engine.connect() as conn:
        results = conn.execute(playersQuery).fetchall()
        if results:
            players = results

    # Get Team record
    recordQuery = text(f'''
        SELECT
            (SELECT
                SUM(CASE WHEN seriesWinner = {team.id} THEN 1 ELSE 0 END)
                FROM Series
                WHERE id IN (
                    SELECT DISTINCT Series_id
                    FROM Stats
                    WHERE League_id = {league.id})
            ) AS seriesWins,
            (SELECT
                SUM(CASE WHEN seriesLoser = {team.id} THEN 1 ELSE 0 END)
                FROM Series
                WHERE id IN (
                    SELECT DISTINCT Series_id
                    FROM Stats
                    WHERE League_id = {league.id})
            ) AS seriesLosses,
            COUNT(CASE WHEN winningTeam = {team.id} THEN 1 END) AS gameWins,
            COUNT(CASE WHEN winningTeam <> {team.id} THEN 1 END) AS gameLosses
        FROM Stats
        WHERE League_id = {league.id}
            AND (Team0_id = {team.id} OR Team1_id = {team.id})
            AND winningTeam IS NOT NULL;
    ''')

    with db.engine.connect() as conn:
        record = conn.execute(recordQuery).first()

    # Assign the wins and losses to the team object
    team.seriesWins = record.seriesWins
    team.seriesLosses = record.seriesLosses
    team.gameWins = record.gameWins
    team.gameLosses = record.gameLosses

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
        return render_template('team.html', user=current_user, team_id=team_id, current_team=team, numberInQueue=numberInQueue, current_league=league, players=players)
    if league.isPlayoffs == 0:

        # Get all season matchups from Stats table associated with the League.id and Team.id
        matchupQuery = text(f'''
            SELECT s.Series_id, s.Team0_id, s.Team1_id, t1.teamName AS Team0_name, t2.teamName AS Team1_name,
                COUNT(CASE WHEN s.winningTeam = s.Team0_id THEN 1 END) AS Team0_wins,
                COUNT(CASE WHEN s.winningTeam = s.Team1_id THEN 1 END) AS Team1_wins,
                t1.team_banner, t2.team_banner
            FROM Stats s
            JOIN Team t1 ON s.Team0_id = t1.id
            JOIN Team t2 ON s.Team1_id = t2.id
            WHERE s.League_id = {league.id} AND round_one = 0 AND round_two = 0 AND round_three = 0 AND (s.Team0_id = {team_id} OR s.Team1_id = {team_id})
            GROUP BY s.Series_id, s.Team0_id, s.Team1_id, t1.teamName, t2.teamName;
        ''')

        with db.engine.connect() as conn:
            matchList = conn.execute(matchupQuery).fetchall()

        match_num = 1
        matchups = {}
        for row in matchList:
            series_id = row[0]  # Use integer index instead of string index
            matchups[series_id] = {
                "Match_num": match_num,
                "Team0_id": row[1],
                "Team0_name": row[3],
                "Team0_wins": row[5],
                "Team0_banner": row[7],
                "Team1_id": row[2],
                "Team1_name": row[4],
                "Team1_wins": row[6],
                "Team1_banner": row[8]
            }
            match_num = match_num + 1

        return render_template('team.html', user=current_user, team_id=team_id, current_team=team, current_league=league, matchups=matchups, players=players)

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

            return render_template('team.html', user=current_user, team_id=team_id, current_team=team, current_league=league, playoffSeries=playoffSeries, round_name=round_name, players=players)
        
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

            return render_template('team.html', user=current_user, team_id=team_id, current_team=team, current_league=league, playoffSeries=playoffSeries, round_name=round_name, players=players)
        
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

            return render_template('team.html', user=current_user, team_id=team_id, current_team=team, current_league=league, playoffSeries=playoffSeries, round_name=round_name, players=players)


@views.route('/match') #TODO: Get usernames, use profile image, team logo and team banner to pass to template
def match():
    # Get both Team.id's and League.id from args for current matchup
    team_id = request.args.get('team_id')
    current_league_id = request.args.get('current_league')
    series_id = request.args.get('series_id')

    # Get object from Series table
    series = Series.query.filter_by(id=series_id).first()

    # Get Teams and rosters for the current Series.id
    teamsQuery = text(f'''
        SELECT * FROM (
            SELECT l.team_id, t.teamName,
                COALESCE(subquery.wins, 0) AS seriesWins,
                COALESCE(subquery3.gameWins, 0) AS gameWins,
                COALESCE(subquery2.losses, 0) AS seriesLosses,
                COALESCE(subquery4.gameLosses, 0) AS gameLosses,
                t.team_logo, t.team_banner
            FROM League l
            LEFT JOIN (
                SELECT s.seriesWinner, COUNT(s.seriesWinner) AS wins
                FROM Series s
                WHERE s.id IN (SELECT Series_id FROM Stats WHERE League_id = {current_league_id})
                GROUP BY s.seriesWinner
            ) AS subquery ON l.team_id = subquery.seriesWinner
            LEFT JOIN (
                SELECT s.seriesLoser, COUNT(s.seriesLoser) AS losses
                FROM Series s
                WHERE s.id IN (SELECT Series_id FROM Stats WHERE League_id = {current_league_id})
                GROUP BY s.seriesLoser
            ) AS subquery2 ON l.team_id = subquery2.seriesLoser
            LEFT JOIN (
                SELECT s.winningTeam, COUNT(s.winningTeam) AS gameWins
                FROM Stats s
                WHERE s.League_id = {current_league_id}
                GROUP BY s.winningTeam
            ) AS subquery3 ON l.team_id = subquery3.winningTeam
            LEFT JOIN (
                SELECT s.losingTeam, COUNT(s.losingTeam) AS gameLosses
                FROM Stats s
                WHERE s.League_id = {current_league_id}
                GROUP BY s.losingTeam
            ) AS subquery4 ON l.team_id = subquery4.losingTeam
            JOIN Team t ON l.team_id = t.id
            WHERE l.id = {current_league_id} AND 
            l.team_id IN (SELECT Team1_id FROM Stats WHERE Series_id = {series.id}) OR
            l.team_id IN (SELECT Team0_id FROM Stats WHERE Series_id = {series.id})
        ) AS subquery5
        GROUP BY team_id     
    ''')
    
    userQuery = text(f'''
        SELECT tp.teamId, u.username, u.profile_image
        FROM TeamPlayers tp
        JOIN Team t ON tp.teamId = t.id
        JOIN User u ON tp.userId = u.id
        WHERE tp.teamId IN (SELECT Team0_id FROM Stats WHERE Series_id = {series.id})
        OR tp.teamId IN (SELECT Team1_id FROM Stats WHERE Series_id = {series.id});          
    ''')
    
    # Query to get Users stat lines for the specific Series.id
    userStatsQuery = text(f'''
        SELECT  u.username, us.score, us.goals, us.assists, us.saves, us.shots
        FROM UserStats us
        JOIN User u ON us.User_id = u.id
        WHERE Series_id = {series.id}
    ''')

    stats = ()
    
    with db.engine.connect() as conn:
        teams = conn.execute(teamsQuery).all()
        users =conn.execute(userQuery).all()
        if series.seriesWinner:
            stats = conn.execute(userStatsQuery).all()

    team_stats = {}
    for team in teams:
        teamId = team.team_id
        team_stats[teamId] = {
            'teamName': team.teamName,
            'seriesWins': team.seriesWins,
            'gameWins': team.gameWins,
            'seriesLosses': team.seriesLosses,
            'gameLosses': team.gameLosses,
            'team_logo': team.team_logo,
            'team_banner': team.team_banner,
            'users': []
        }

    # Update the loop below to use team_stats instead of teams
    for user in users:
        teamId = user.teamId
        user_data = {
            'username': user.username,
            'profile_image': user.profile_image
        }
        team_stats[teamId]['users'].append(user_data)

    first_team_id = list(team_stats.keys())[0]
    second_team_id = list(team_stats.keys())[1]
    teamNames = [team_stats[first_team_id]['teamName'], team_stats[second_team_id]['teamName']]

    return render_template('match.html', user=current_user, current_league_id=current_league_id, series=series, team_stats=team_stats, stats=stats, teamNames=teamNames, team_id=team_id)

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
    # Get League.id and Team.id from args
    team_id = request.args.get('team_id')
    current_league_id = request.args.get('current_league_id')
    series_id = request.args.get('series_id')

    # Get the Stats object for specific Series.id
    series = Stats.query.filter_by(Series_id=series_id).first()

    current_team = series.Team0_id
    opponent_team = series.Team1_id

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
                                team_id=team_id,
                                current_team_name=current_team.teamName,
                                opponent_team_name=opponent_team.teamName,
                                current_team_dict=current_team_dict,
                                opponent_team_dict=opponent_team_dict,
                                current_league_id=current_league_id,
                                series_id=series_id
                            )

@views.route('/league')
def league():
    # Get Team.id from args
    team_id = request.args.get('team_id')
    # Get the League object associated with the current_team
    league = League.query.filter(League.team_id == team_id, League.isActive == True).first()

    # Query to get Team Users and their respective info
    query = text(f'''
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
            WHERE s.id IN (SELECT Series_id FROM Stats WHERE League_id = {league.id})
            GROUP BY s.seriesWinner
        ) AS subquery ON l.team_id = subquery.seriesWinner
        LEFT JOIN (
            SELECT s.seriesLoser, COUNT(s.seriesLoser) AS losses
            FROM Series s
            WHERE s.id IN (SELECT Series_id FROM Stats WHERE League_id = {league.id})
            GROUP BY s.seriesLoser
        ) AS subquery2 ON l.team_id = subquery2.seriesLoser
        LEFT JOIN (
            SELECT s.winningTeam, COUNT(s.winningTeam) AS gameWins
            FROM Stats s
            WHERE s.League_id = {league.id}
            GROUP BY s.winningTeam
        ) AS subquery3 ON l.team_id = subquery3.winningTeam
        LEFT JOIN (
            SELECT s.losingTeam, COUNT(s.losingTeam) AS gameLosses
            FROM Stats s
            WHERE s.League_id = {league.id}
            GROUP BY s.losingTeam
        ) AS subquery4 ON l.team_id = subquery4.losingTeam
        JOIN Team t ON l.team_id = t.id
        WHERE l.id = {league.id}
    ) AS subquery5
    ORDER BY place;
    ''')

    # Query to get Users for the specific League.id along with a sum of all of their UserStats and a count of how many games they've played
    userStatsQuery = text(f'''
        SELECT tp.teamId, tp.userId, u.username, u.profile_image,
            (SELECT COALESCE(SUM(us.score), 0) FROM UserStats us WHERE us.User_id = tp.userId AND us.Series_id IN (SELECT Series_id FROM Stats WHERE League_id = {league.id})) AS score,
            (SELECT COALESCE(SUM(us.goals), 0) FROM UserStats us WHERE us.User_id = tp.userId AND us.Series_id IN (SELECT Series_id FROM Stats WHERE League_id = {league.id})) AS goals,
            (SELECT COALESCE(SUM(us.assists), 0) FROM UserStats us WHERE us.User_id = tp.userId AND us.Series_id IN (SELECT Series_id FROM Stats WHERE League_id = {league.id})) AS assists,
            (SELECT COALESCE(SUM(us.saves), 0) FROM UserStats us WHERE us.User_id = tp.userId AND us.Series_id IN (SELECT Series_id FROM Stats WHERE League_id = {league.id})) AS saves,
            (SELECT COALESCE(SUM(us.shots), 0) FROM UserStats us WHERE us.User_id = tp.userId AND us.Series_id IN (SELECT Series_id FROM Stats WHERE League_id = {league.id})) AS shots,
            (SELECT COUNT(*) FROM UserStats us WHERE us.User_id = tp.userId AND us.Series_id IN (SELECT Series_id FROM Stats WHERE League_id = {league.id})) AS games_played
            FROM League l
            JOIN TeamPlayers tp ON l.team_id = tp.teamId
            JOIN User u ON tp.userId = u.id
            WHERE l.id = {league.id}
            ORDER BY goals DESC;
    ''')

    with db.engine.connect() as conn:
        league = conn.execute(query).fetchall()
        userStats = conn.execute(userStatsQuery).fetchall()

    saves_sort = sorted(userStats, key=lambda x: x.saves, reverse=True)
    most_saves = saves_sort[0]

    assists_sort = sorted(userStats, key=lambda x: x.assists, reverse=True)
    most_assists = assists_sort[0]

    # Create team dictionaries and nest respective User dictionaries inside
    place = 1
    team_stats = {}
    for team in league:
        team_id = team.team_id
        team_stats[team_id] = {
            'place': place,
            'teamName': team.teamName,
            'seriesWins': team.seriesWins,
            'gameWins': team.gameWins,
            'seriesLosses': team.seriesLosses,
            'gameLosses': team.gameLosses,
            'team_logo': team.team_logo,
            'team_banner': team.team_banner,
            'users': []
        }
        place = place + 1

    for user in userStats:
        team_id = user.teamId
        user_data = {
            'userId': user.userId,
            'username': user.username,
            'profile_image': user.profile_image,
            'score': user.score,
            'goals': user.goals,
            'assists': user.assists,
            'saves': user.saves,
            'shots': user.shots,
            'games_played': user.games_played
        }
        team_stats[team_id]['users'].append(user_data)

    return render_template('league.html', user=current_user, team_stats=team_stats, userStats=userStats, most_saves=most_saves, most_assists=most_assists)

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