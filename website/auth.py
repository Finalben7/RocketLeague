from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import or_
from flask_mail import Message
import jwt
from flask import current_app

auth = Blueprint('auth', __name__)

################# Function to verift JWT token passed as an argument from resetEmail.html #################
def verifyResetToken(token):
    try:
        secret_key = current_app.config['SECRET_KEY']
        decoded_token = jwt.decode(token, key=secret_key, algorithms=['HS256'])
        username = decoded_token['reset_password']
        print(secret_key, decoded_token, username)
    except jwt.exceptions.DecodeError:
        flash('Invalid or expired reset token.', category='error')
        return render_template('login.html', user=current_user)
    return User.query.filter_by(username=username).first()


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

################# Request Email To Reset Password #################
@auth.route('/requestPasswordReset', methods=['GET', 'POST'])
def requestPasswordReset():
    if request.method == 'POST':
        # Get email address entered into form
        email = request.form.get('email')

        # Get User object associated with email address from form
        user = User.query.filter(User.email == email).first()

        if user:

            token = jwt.encode({'reset_password': user.username}, key = current_app.config['SECRET_KEY'])

            msg = Message()
            msg.subject = "Reset your Underground account's password"
            msg.recipients = [user.email]
            msg.sender = 'eleventhhouresports@gmail.com'
            msg.html = render_template('resetEmail.html', user=user, token=token)

            mail.send(msg)
            flash(f"Email has been sent to {user.email}, please follow the link provided to reset your password.", category='success')
            return render_template('requestPasswordReset.html', user=current_user)
        else:
            flash('Email address not found.', category='error')
            return render_template('requestPasswordReset.html', user=current_user)
    
    return render_template('requestPasswordReset.html', user=current_user)

################# Verification Email #################
@auth.route('/resetEmail', methods=['GET', 'POST'])
def resetEmail():

    return render_template('resetEmail.html', user=current_user)

@auth.route('/resetVerified/<token>', methods=['GET', 'POST'])
def resetVerified(token):
    
    user = verifyResetToken(token)
    print(user.username)

    if not user:
        print('No User Found!')
        flash('Email address not found.', category='error')
        return redirect(url_for('auth.login'))

    newPassword = request.form.get('password')
    if newPassword:
        if len(newPassword) < 6:
            flash("Password must be greater than 6 characters", category='error')
        else:
            print(newPassword)
            user.password = generate_password_hash(newPassword, method='sha256')
            db.session.commit()
            flash('Password successfully updated.', category='success')
            return redirect(url_for('auth.login'))
    
    flash('Reset token verified, please enter a new password.', category='success')
    return render_template('resetVerified.html', user=current_user)