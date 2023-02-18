import mysql.connector

from flask import Flask
from flask_mysqldb import MySQL
from . import glblvars

DB_NAME = "RL"
DB_PORT = 3660

def dbconnect(app):
    mysql = MySQL()
    # MySQL credentials
    app.config['MYSQL_HOST'] = glblvars.DB_HOST
    app.config['MYSQL_USER'] = glblvars.DB_USER
    app.config['MYSQL_PASSWORD'] = glblvars.DB_PASS
    app.config['SECRET_KEY'] = glblvars.SECRET_KEY
    app.config['MYSQL_DB'] = DB_NAME
    app.config['MYSQL_PORT'] = DB_PORT
    mysql.init_app(app)

    

    """
    Example code for SQL statements

    cursor.execute(''' CREATE TABLE table_name(field1, field2...) ''')
    cursor.execute(''' INSERT INTO table_name VALUES(v1,v2...) ''')
    cursor.execute(''' DELETE FROM table_name WHERE condition ''')

    db.commit()  # save actions performed
    cursor.close()  # disconnect
    """
    
    with app.app_context():
        # db = mysql.connect()    # Create connection cursor so Flask see tables
        cursor = mysql.connect.cursor()    # Create cursor to interact with tables
    
    # test to see if we can query the db.    
    # cursor.execute("SELECT * from Users")
    # data = cursor.fetchall()
    # print(data)
    
    return cursor