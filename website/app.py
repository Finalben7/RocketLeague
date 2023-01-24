"""
SQLAlchemy ----> MySQL transition
"""

from flask import Flask, render_template, request
from flask_mysqldb import MySQL

from .views import views
from .auth import auth
from .models import User, Note

DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)

    # MySQL credentials
    app.config['SECRET_KEY'] = 'secretkeytest'  # needed?
    app.config['MYSQL_HOST'] = ''  #FIXME
    app.config['MYSQL_USER'] = ''  #FIXME
    app.config['MYSQL_PASSWORD'] = ''  #FIXME
    app.config['MYSQL_DB'] = DB_NAME  #FIXME

    mysql = MySQL(app)

    """
    Example code for SQL statements

    cursor = mysql.connection.cursor()  # Create connection cursor so Flask can interact with tables
    cursor.execute(''' CREATE TABLE table_name(field1, field2...) ''')
    cursor.execute(''' INSERT INTO table_name VALUES(v1,v2...) ''')
    cursor.execute(''' DELETE FROM table_name WHERE condition ''')

    mysql.connection.commit()  # save actions performed
    cursor.close()  # disconnect
    """

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app