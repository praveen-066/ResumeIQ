from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from flask_mail import Mail, Message
from utils.decorators import admin_required
from models import db, User, Resume, SMTPConfig

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/')
@login_required
@admin_required
def dashboard():
    users = User.query.all()
    resumes = Resume.query.order_by(Resume.created_at.desc()).all()
    
    # Calculate Metrics
    avg_score = 0
    if resumes:
        total_score = sum(r.score for r in resumes)
        avg_score = round(total_score / len(resumes), 1)

    # Prepare Chart Data
    chart_labels = [r.filename for r in resumes[:10]] # limit to 10 recent
    chart_data = [r.score for r in resumes[:10]]
    
    return render_template('admin_dashboard.html', users=users, resumes=resumes, avg_score=avg_score, chart_labels=chart_labels, chart_data=chart_data)

@admin.route('/delete_user/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot delete admin user', 'error')
        return redirect(url_for('admin.dashboard'))
    
    try:
        # Delete associated resumes first (though cascade usually handles this)
        Resume.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {e}', 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin.route('/delete_resume/<int:resume_id>')
@login_required
@admin_required
def delete_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    try:
        db.session.delete(resume)
        db.session.commit()
        flash('Resume deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting resume: {e}', 'error')
        
    return redirect(url_for('admin.dashboard'))

@admin.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    config = SMTPConfig.query.first()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        server = request.form.get('server')
        port = int(request.form.get('port'))
        username = request.form.get('username')
        password = request.form.get('password')
        use_tls = 'use_tls' in request.form
        
        if not config:
            config = SMTPConfig(server=server, port=port, username=username, password=password, use_tls=use_tls)
            db.session.add(config)
        else:
            config.server = server
            config.port = port
            config.username = username
            config.password = password
            config.use_tls = use_tls
            
        db.session.commit()
        
        if action == 'save':
            flash('Settings saved successfully', 'success')
        elif action == 'test':
            # Send Test Email
            from flask import current_app
            
            # Configure Mail dynamically
            current_app.config['MAIL_SERVER'] = config.server
            current_app.config['MAIL_PORT'] = config.port
            current_app.config['MAIL_USERNAME'] = config.username
            current_app.config['MAIL_PASSWORD'] = config.password
            current_app.config['MAIL_USE_TLS'] = config.use_tls
            current_app.config['MAIL_USE_SSL'] = False
            
            mail = Mail(current_app)
            try:
                msg = Message("ResumeIQ Test Email", 
                            sender=config.username, 
                            recipients=[current_user.username if '@' in current_user.username else config.username])
                msg.body = "This is a test email to verify your SMTP settings."
                mail.send(msg)
                flash(f'Test email sent to {msg.recipients[0]}', 'success')
            except Exception as e:
                flash(f'Failed to send email: {e}', 'error')
                
        return redirect(url_for('admin.settings'))
        
    return render_template('admin_settings.html', config=config)
