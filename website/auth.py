from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import or_
from datetime import datetime, timedelta


auth = Blueprint('auth', __name__)

################# Login #################
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect user/password, try again', category='error')
                
    # print(data)
    return render_template('login.html', user=current_user)

################# Logout #################
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

################# Signup #################
@auth.route('/signup', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        username = request.form.get('username')
        platform = request.form.get('platform')
        region = request.form.get('region')
        discord = request.form.get('discord')
        user = User.query.filter(or_(User.email == email, User.username == username, User.discord == discord)).first()
        if user:
            if user.email == email:
                flash('This email address is already in use.', category='error')
            elif len(email) < 6:
                flash("Email must be greater than 6 characters", category='error')
            elif user.username == username:
                flash('This username is already in use.', category='error')
            elif user.discord == discord:
                flash('This discord is already linked with an Underground account.', category='error')
        elif password1 != password2:
            flash("Passwords must match", category='error')
        elif len(password1) < 6:
            flash("Password must be greater than 6 characters", category='error')
        else:
            new_user = User(email=email, password=generate_password_hash(password1, method='sha256'), username=username, platform=platform, region=region, discord=discord)
            db.session.add(new_user)
            db.session.commit()
            # print(new_user)  
            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('views.home'))
                       
    return render_template('signup.html', user=current_user)

################# Reset Password #################
@auth.route('/resetPassword', methods=['GET', 'POST'])
def resetPassword():
    print("Reset Password Has Been Called!")
    if request.method == 'POST':
        # Get email address entered into form
        email = request.form.get('email')

        # Get User object associated with email address from form
        user = User.query.filter(User.email == email).first()

        if user:
            reset_token = generate_password_hash(user.email + str(datetime.now()))
            reset_token_expiration = datetime.now() + timedelta(hours=1)
            db.session.commit()
            print(reset_token)
            print(reset_token_expiration)
        else:
            flash('Email address not found.', category='error')
            return redirect(url_for('resetPassword.html'))
    
    return render_template('resetPassword.html')