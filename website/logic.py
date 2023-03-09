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
            return render_template('teams.html', user=current_user)
        else: flash('The teammate information you entered is not valid, please double check the form.', category='error')
        return render_template('createTeam.html', user=current_user)







#Queue and league generation logic
# @logic.route('/joinQueue', methods=['GET', 'POST'])
# def joinQueue():
#     team = request.args.get('team')
#     usernames = request.args.get('usernames')
#     print("test!")
#     return render_template('team.html', user=current_user, team=team, usernames=usernames)



#Queue and league generation logic
# @logic.route('/joinQueue', methods=['GET', 'POST'])
# def joinQueue():
#     if request.method == 'POST':
#         queueToJoin = None  # TODO: attach to button

#         team = Team.query.filter(Team.teamCaptain == current_user.id).first()

#         if len(queueToJoin) >= 8:
#             flash("Queue is full!", category='error')
#             return render_template('joinQueue.html', user=current_user) 
        
#         if queueToJoin.rank != team.rank:
#             flash("Queue rank does not match team rank!", category='error')
#             return render_template('joinQueue.html', user=current_user)
        
#         if queueToJoin.region != team.region:
#             flash("Queue region does not match team region!", category='error')
#             return render_template('joinQueue.html', user=current_user)

#         queueToJoin.teams.append(teamID)
#         if len(queueToJoin) == 8:
#             for teamID in queueToJoin:
#                 newLeague = league(teamID = teamID, teamName = teamName, record = record)
#                 db.session.add = newLeague(league)

#         db.session.commit()
#         flash('Queue joined!', category='success')
#         return render_template('team.html', user=current_user) 
        
#     elif request.method == 'GET':
#         team = Team.query.filter(Team.teamCaptain == current_user.id).first()

#         query = f'''
#         SELECT q.teams, q.rank, q.region
#         FROM Queue q
#         '''

#         with db.engine.connect() as conn:
#             queueList = conn.execute(query).fetchall()

#         filteredQueues = [q for q in queueList if ((q.rank == team.rank) and (q.region == team.region))]
        
#         if not filteredQueues:
#             flash('No queues currently available, feel free to create your own!', category='error')
#             return render_template("joinQueue.html", user=current_user)

#        return render_template()  # TODO: queue template




# @logic.route('/createQueue', methods=['POST'])
# def createQueue():
#     if request.method == 'POST':
#         teamID = request.form.get('teamID')
#         teamName = request.form.get('teamName')
#         record = request.form.get('record')

#         # Create Queue object and populate
#         newQueue = Queue()  # FIXME
#         newQueue.teams = deque()
#         newQueue.teams.append(team)
#         newQueue.rank = team.rank
#         newQueue.region = team.region

#         # Commit changes to database
#         db.session.add(newQueue)
#         db.session.commit()