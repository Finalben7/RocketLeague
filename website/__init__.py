from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mysqldb import MySQL
from . import glblvars

db = SQLAlchemy()

def create_app():
    # print(glblvars.DB_HOST)
    app = Flask(__name__)
    mysql = MySQL(app)
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

    
    app.config['SECRET_KEY'] = 'secretkeytest'
    
    # MySQL-Python
    # mysql+mysqldb://<user>:<password>@<host>[:<port>]/<dbname>
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root:@localhost/underground" #TOM'S "mysql+mysqldb://RLuser:FearTheLemon11!!@ix.cs.uoregon.edu:3660/RL1"
    
    db.init_app(app)

    from .views import views
    from .auth import auth
    from .logic import logic
    
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(logic, url_prefix='/')
    
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