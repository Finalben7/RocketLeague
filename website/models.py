from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint, Index, Sequence

Base = declarative_base()

class User(db.Model,  UserMixin):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    username = db.Column(db.String(150), unique=True)
    platform = db.Column(db.String(150))
    region = db.Column(db.String(150))
    rank = db.Column(db.Numeric(2, 0), default=15)
    Index("userIdIndex", "id", "email", "username" )

class Team(db.Model):
    __tablename__ = 'Team'
    id = db.Column(db.Integer, primary_key=True)
    teamName = db.Column(db.String(32))
    rank = db.Column(db.String(150))
    region = db.Column(db.String(150))
    teamCaptain = db.Column(db.Integer, ForeignKey("User.id"))
    isQueued = db.Column(db.Boolean, default=0)
    isActive = db.Column(db.Boolean, default=0)

class League(db.Model):
    __tablename__ = 'League'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, ForeignKey("Team.id"))

class Series(db.Model):
    __tablename__ = 'Series'
    id = db.Column(db.Integer, primary_key=True)
    seriesWinner = db.Column(db.Integer, ForeignKey("Team.id"))

class Stats(db.Model):
    __tablename__ = 'Stats'
    id = db.Column(db.Integer, primary_key=True)
    Series_id = db.Column(db.Integer, ForeignKey("Series.id"))
    winningTeam = db.Column(db.Integer, ForeignKey("Team.id"))
    #Team_id = db.Column(db.Integer, ForeignKey("Team.id"))
    #userId = db.Column(db.Integer, ForeignKey("User.id"))
    # score = db.Column(db.Numeric(4, 0))
    # goals = db.Column(db.Numeric(2, 0))
    # assists = db.Column(db.Numeric(2, 0))
    # saves = db.Column(db.Numeric(2, 0))
    # shots = db.Column(db.Numeric(2, 0))

class TeamPlayers(db.Model):
    __tablename__ = 'TeamPlayers'
    userId = db.Column(db.Integer, ForeignKey("User.id"), primary_key=True)
    teamId = db.Column(db.Integer, ForeignKey("Team.id"), primary_key=True)
