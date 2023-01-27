from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
# from . import db
from flask_login import login_user, login_required, logout_user, current_user
import subprocess



auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('logged in!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('incorrect user/password, try again', category='error')
                
    # print(data)
    return render_template('login.html', user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/signup', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        username = request.form.get('username')
        platform = request.form.get('platform')
        region = request.form.get('region')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists', category='error')
        elif len(email) < 6:
            flash("Email must be greater than 6 characters", category='error')
        elif password1 != password2:
            flash("Passwords must match", category='error')
        elif len(password1) < 6:
            flash("Password must be greater than 6 characters", category='error')
        else:
            new_user = User(email=email, password=generate_password_hash(password1, method='sha256'), username=username, platform=platform, region=region)
            # db.session.add(new_user)
            # db.session.commit()
            # print(new_user)
            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('views.home'))
                       
    return render_template('signup.html', user=current_user)

def verify_user(user):
    pass
    # username = user.username
    # platform = user.platform
    # path = f'php ./rankdata.php?user={username}&platform={platform}'
    # print(path)
    # result = subprocess.Popen([path], stdout=subprocess.PIPE, shell=True)
    # response = result.stdout.read()
    # print(result.stdout)