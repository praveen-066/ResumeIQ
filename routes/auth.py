from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models import db, User

auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Check if JSON request (AJAX)
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
        else:
             username = request.form.get('username')
             email = request.form.get('email')
             password = request.form.get('password')
        
        # Validation
        if not username or not email or not password:
             if request.is_json:
                return jsonify({'success': False, 'message': 'All fields are required'}), 400
             flash('All fields are required', 'error')
             return redirect(url_for('auth.register'))

        # Gmail Validation
        if not email or not email.lower().endswith('@gmail.com'):
             if request.is_json:
                return jsonify({'success': False, 'message': 'Please enter a valid Gmail address (@gmail.com)'}), 400
             flash('Please enter a valid Gmail address (@gmail.com)', 'error')
             return redirect(url_for('auth.register'))

        if User.query.filter((User.username==username) | (User.email==email)).first():
            if request.is_json:
                return jsonify({'success': False, 'message': 'Username or Email already exists'}), 400
            flash('Username or Email already exists', 'error')
            return redirect(url_for('auth.register'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password, role='user')
        
        try:
            db.session.add(new_user)
            db.session.commit()
            if request.is_json:
                return jsonify({'success': True, 'message': 'Account created! Logging in...', 'redirect': url_for('auth.login')})
            flash('Account created! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            if request.is_json:
                return jsonify({'success': False, 'message': str(e)}), 500
            flash(f'Error creating account: {e}', 'error')
            
    return render_template('auth_combined.html', mode='register')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            login_id = (data.get('email') or data.get('username') or '').strip()
            password = data.get('password')
        else:
            login_id = (request.form.get('email') or request.form.get('username') or '').strip()
            password = request.form.get('password')

        # Try to find user by email or username
        user = User.query.filter((User.email == login_id) | (User.username == login_id)).first()
        
        if not user:
             if request.is_json:
                return jsonify({'success': False, 'message': "User doesn't exist. Please register."}), 401
             flash("User doesn't exist. Please register.", 'error')
             return redirect(url_for('auth.login'))

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            
            # Role-based redirect logic
            if user.role == 'admin':
                default_target = url_for('admin.dashboard')
            else:
                default_target = url_for('main.dashboard')
            
            next_page = request.args.get('next')
            target = next_page if next_page else default_target

            if request.is_json:
                return jsonify({'success': True, 'redirect': target})
            return redirect(target)
        else:
             if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid password'}), 401
             flash('Invalid password', 'error')
            
    return render_template('auth_combined.html', mode='login')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
