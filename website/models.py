# from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func

class User(UserMixin):
    id = 'test'
    password = 'test'
    username = 'test'
    email = 'test'