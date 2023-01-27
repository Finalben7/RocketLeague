from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path, environ
from flask_login import LoginManager
from flask_mysqldb import MySQL
from . import glblvars

# db = SQLAlchemy()
DB_NAME = "RL"
DB_PORT = '3660'

def create_app():
    # print(glblvars.DB_HOST)
    app = Flask(__name__)
    mysql = MySQL()
    # app.config['SECRET_KEY'] = 'secretkeytest'
    # MySQL credentials
    # app.config['SECRET_KEY'] = environ.get('SECRET_KEY')  # needed?
    # app.config['MYSQL_HOST'] = environ.get('DB_HOST')  #FIXME
    # app.config['MYSQL_USER'] = environ.get('DB_USER')  #FIXME
    # app.config['MYSQL_PASSWORD'] = environ.get('DB_PASS')  #FIXME
    app.config['MYSQL_HOST'] = glblvars.DB_HOST  #FIXME
    app.config['MYSQL_USER'] = glblvars.DB_USER
    app.config['MYSQL_PASSWORD'] = glblvars.DB_PASS  #FIXME
    app.config['SECRET_KEY'] = glblvars.SECRET_KEY
    app.config['MYSQL_DB'] = DB_NAME  #FIXME
    app.config['MYSQL_PORT'] = DB_PORT
    # app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + DB_NAME

    

    """
    Example code for SQL statements

    cursor = mysql.connection.cursor()  # Create connection cursor so Flask can interact with tables
    cursor.execute(''' CREATE TABLE table_name(field1, field2...) ''')
    cursor.execute(''' INSERT INTO table_name VALUES(v1,v2...) ''')
    cursor.execute(''' DELETE FROM table_name WHERE condition ''')

    mysql.connection.commit()  # save actions performed
    cursor.close()  # disconnect
    """
    
    # db.init_app(app)
    with app.app_context():
        cursor = mysql.connect.cursor()  # Create connection cursor so Flask can interact with tables
    
    from .views import views
    from .auth import auth
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    
    from .models import User
    
    # with app.app_context():
    #     db.create_all()
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    return app, cursor