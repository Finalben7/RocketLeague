"""
Author: Niklaas Cotta
Last Updated: 3/3/2023
Desc: Queue system for matchmaking
"""

from collections import deque
from . import db
from flask import flash

def createQueue(team):
    newQueue = Queue()
    newQueue.teams = deque()
    newQueue.teams.append(team)
    newQueue.rank = team.rank
    newQueue.region = team.region

    db.session.add(newQueue)
    db.session.commit()


def joinQueue(team):
    query = f'''
    SELECT q.teams, q.rank, q.region
    FROM Queue q
    '''

    with db.engine.connect() as conn:
        queueList = conn.execute(query).fetchall()

    filteredQueues = [q for q in queueList if ((q.rank == team.rank) and (q.region == team.region))]
    if not filteredQueues:
        createQueue(team)
    
    print("Join a queue that already has a team")

    for queue in filteredQueues:
        print(queue)
        print(f"Queue has {len(queue.teams)} teams out of 8 total")


    queueToJoin = input("Select queue to join...")  # FIXME

    if len(queueToJoin) >= 8:
        flash("Queue is full!", category='error')
        return False
    
    if queueToJoin.rank != team.rank:
        flash("Queue rank does not match team rank!", category='error')
        return False
    
    if queueToJoin.region != team.region:
        flash("Queue region does not match team region!", category='error')
        return False
    
    print("Or create your own!")
    if input() == "new":  # FIXME
        createQueue(team)
    
    queueToJoin.teams.append(team)
    db.session.commit()

    return True