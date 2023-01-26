from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path, environ
from flask_login import LoginManager
from flask_mysqldb import MySQL

# db = SQLAlchemy()
DB_NAME = "RL"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secretkeytest'
    # MySQL credentials
    app.config['SECRET_KEY'] = environ.get('SECRET_KEY')  # needed?
    app.config['MYSQL_HOST'] = environ.get('DB_HOST')  #FIXME
    app.config['MYSQL_USER'] = environ.get('DB_USER')  #FIXME
    app.config['MYSQL_PASSWORD'] = environ.get('DB_PASS')  #FIXME
    app.config['MYSQL_DB'] = DB_NAME  #FIXME
    # app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + DB_NAME

    mysql = MySQL(app)

    cursor = mysql.connect.cursor()  # Create connection cursor so Flask can interact with tables

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
    
    from .views import views
    from .auth import auth
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    
    from .models import User, Note
    
    # with app.app_context():
    #     db.create_all()
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    return app