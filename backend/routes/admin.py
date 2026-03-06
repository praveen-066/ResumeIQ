from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from flask_mail import Mail, Message
from utils.decorators import admin_required, recruiter_required
from models import db, User, Resume, SMTPConfig, ParsedData, Inquiry, JobDescription
from utils.constants import get_all_roles, TARGET_ROLES
from utils.extractor import extract_text
from utils.scorer import calculate_ats_score, calculate_jd_match_score
from utils.analyzer import parse_resume, analyze_skill_gap
from mongo_models import AtsScore
import uuid
import os
import json

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/')
@login_required
def admin_root():
    if current_user.role in ['admin', 'recruiter']:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('main.dashboard'))

@admin.route('/dashboard')
@login_required
@recruiter_required
def dashboard():
    users = User.query.all()
    resumes = Resume.query.order_by(Resume.created_at.desc()).all()
    
    # Calculate Metrics
    avg_score = 0
    shortlisted_count = AtsScore.objects(status='Shortlisted').count()
    
    if resumes:
        total_score = sum(r.score for r in resumes)
        avg_score = round(total_score / len(resumes), 1)

    # Prepare Chart Data
    chart_labels = [r.filename for r in resumes[:10]] # limit to 10 recent
    chart_data = [r.score for r in resumes[:10]]
    
    return render_template('admin_dashboard.html', 
                          users=users, 
                          resumes=resumes, 
                          avg_score=avg_score, 
                          shortlisted_count=shortlisted_count,
                          chart_labels=chart_labels, 
                          chart_data=chart_data)

@admin.route('/candidates')
@login_required
@recruiter_required
def candidates():
    from utils.constants import get_all_roles, TARGET_ROLES
    role = request.args.get('role', 'All')
    score_min = request.args.get('score_min', 0, type=int)
    batch_id = request.args.get('batch_id')
    
    query = Resume.query
    
    if batch_id:
        query = query.filter_by(batch_id=batch_id)
    elif role == 'All' and score_min == 0:
        # If no filters and no batch, show empty or latest 5 with a message
        # For now, let's show nothing if batch_id is not provided but requested filters are empty
        query = query.filter(Resume.id == -1) # return empty
    
    if role != 'All':
        query = query.filter_by(role_applied=role)
    
    if score_min > 0:
        query = query.filter(Resume.score >= score_min)
        
    candidates = query.order_by(Resume.score.desc()).all()
    
    # Get all possible roles from constants
    roles = get_all_roles()
    
    return render_template('admin_candidates.html', 
                          candidates=candidates, 
                          roles=roles, 
                          target_roles=TARGET_ROLES,
                          selected_role=role,
                          selected_score=score_min,
                          selected_batch=batch_id)

@admin.route('/upload', methods=['GET', 'POST'])
@login_required
@recruiter_required
def upload():
    if request.method == 'POST':
        files = request.files.getlist('resumes')
        target_role = request.form.get('role', 'Software Engineer')
        
        if not files or files[0].filename == '':
            flash('No files selected', 'error')
            return redirect(url_for('admin.upload'))
            
        batch_id = str(uuid.uuid4())[:8]
        processed_count = 0
        
        for file in files:
            if file and file.filename.lower().endswith(('.pdf', '.docx')):
                import secrets
                safe_name = secrets.token_hex(8) + '_' + file.filename
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_name)
                file.save(filepath)
                file_size = os.path.getsize(filepath)
                
                try:
                    text = extract_text(filepath)
                    parsed_data = parse_resume(text)
                    score, breakdown, feedback = calculate_ats_score(parsed_data, target_role)
                    missing_skills = analyze_skill_gap(parsed_data['skills'], target_role)
                    
                    from utils.analyzer import generate_ai_tips
                    dynamic_tips = generate_ai_tips(parsed_data)

                    suggestions = {
                        'strengths': ([f"Found {len(parsed_data['skills'])} relevant skills."]
                                      if parsed_data['skills'] else []),
                        'weaknesses': feedback,
                        'missing_keywords': missing_skills,
                        'improvements': dynamic_tips,
                    }
                    
                    analysis_json = json.dumps({
                        'score': score,
                        'breakdown': breakdown,
                        'details': parsed_data,
                        'suggestions': suggestions,
                        'role': target_role,
                    })

                    resume_entry = Resume(
                        user_id=current_user.id,
                        filename=file.filename,
                        filepath=safe_name,
                        file_size=file_size,
                        score=score,
                        role_applied=target_role,
                        analysis_data=analysis_json,
                        batch_id=batch_id
                    )
                    db.session.add(resume_entry)
                    db.session.flush()

                    parsed_entry = ParsedData(
                        resume_id=resume_entry.id,
                        name=parsed_data.get('name'),
                        email=parsed_data.get('email'),
                        phone=parsed_data.get('phone'),
                        skills=json.dumps(parsed_data.get('skills', [])),
                        experience=json.dumps(parsed_data.get('experience', [])),
                        education=json.dumps(parsed_data.get('education', [])),
                        raw_text=text[:10000],
                    )
                    db.session.add(parsed_entry)
                    processed_count += 1
                except Exception as e:
                    print(f"Error processing {file.filename}: {e}")
                    
        db.session.commit()
        flash(f'Successfully processed {processed_count} resumes in batch {batch_id}', 'success')
        return redirect(url_for('admin.candidates', batch_id=batch_id))
        
    return render_template('admin_upload.html', target_roles=TARGET_ROLES)

@admin.route('/toggle_shortlist/<int:resume_id>')
@login_required
@recruiter_required
def toggle_shortlist(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    ats = AtsScore.objects(resume_id=resume_id).first()
    
    new_status = 'New' if ats and ats.status == 'Shortlisted' else 'Shortlisted'
    
    resume.applicant_status = new_status
    if ats:
        ats.status = new_status
        ats.save()
    
    db.session.commit()
    
    flash(f"Candidate {'shortlisted' if new_status == 'Shortlisted' else 'removed from shortlist'}", 'success')
    return redirect(request.referrer or url_for('admin.candidates'))

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

@admin.route('/inquiries')
@login_required
@recruiter_required
def inquiries():
    inquiries_list = Inquiry.query.order_by(Inquiry.created_at.desc()).all()
    return render_template('admin_inquiries.html', inquiries=inquiries_list)

@admin.route('/delete_inquiry/<int:inquiry_id>')
@login_required
@admin_required
def delete_inquiry(inquiry_id):
    inquiry = Inquiry.query.get_or_404(inquiry_id)
    try:
        db.session.delete(inquiry)
        db.session.commit()
        flash('Inquiry deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting inquiry: {e}', 'error')
    return redirect(url_for('admin.inquiries'))

# ---------------------------------------------------------------------------
# Recruiter Job Workflow Routes
# ---------------------------------------------------------------------------

@admin.route('/jobs', methods=['GET', 'POST'])
@login_required
@recruiter_required
def jobs():
    if request.method == 'POST':
        title = request.form.get('title')
        department = request.form.get('department')
        req_skills_raw = request.form.get('required_skills', '')
        nth_skills_raw = request.form.get('nice_to_have_skills', '')
        exp_level = request.form.get('experience_level', type=int)
        edu_req = request.form.get('education_requirement', '')
        raw_text = request.form.get('raw_text', '')

        req_skills = [s.strip() for s in req_skills_raw.split(',') if s.strip()]
        nth_skills = [s.strip() for s in nth_skills_raw.split(',') if s.strip()]

        jd = JobDescription(
            recruiter_id=current_user.id,
            title=title,
            department=department,
            required_skills=json.dumps(req_skills),
            nice_to_have_skills=json.dumps(nth_skills),
            experience_level=exp_level,
            education_requirement=edu_req,
            raw_text=raw_text
        )
        db.session.add(jd)
        db.session.commit()
        flash('Job created successfully.', 'success')
        return redirect(url_for('admin.jobs'))

    jobs_list = JobDescription.query.order_by(JobDescription.created_at.desc()).all()
    # attach counts
    for j in jobs_list:
        j.applicant_count = Resume.query.filter_by(job_id=j.id).count()

    return render_template('jobs.html', jobs=jobs_list)

@admin.route('/jobs/<int:job_id>/delete')
@login_required
@recruiter_required
def delete_job(job_id):
    jd = JobDescription.query.get_or_404(job_id)
    db.session.delete(jd)
    db.session.commit()
    flash('Job deleted successfully.', 'success')
    return redirect(url_for('admin.jobs'))

@admin.route('/jobs/<int:job_id>/applicants', methods=['GET', 'POST'])
@login_required
@recruiter_required
def job_applicants(job_id):
    jd = JobDescription.query.get_or_404(job_id)
    
    if request.method == 'POST':
        files = request.files.getlist('resumes')
        if not files or files[0].filename == '':
            flash('No files selected', 'error')
            return redirect(url_for('admin.job_applicants', job_id=job_id))
            
        jd_data = {
            "required_skills": json.loads(jd.required_skills) if jd.required_skills else [],
            "nice_to_have_skills": json.loads(jd.nice_to_have_skills) if jd.nice_to_have_skills else [],
            "experience_level": jd.experience_level,
            "education_requirement": jd.education_requirement
        }

        processed_count = 0
        batch_id = str(uuid.uuid4())[:8]
        
        for file in files:
            if file and file.filename.lower().endswith(('.pdf', '.docx')):
                import secrets
                safe_name = secrets.token_hex(8) + '_' + file.filename
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_name)
                file.save(filepath)
                file_size = os.path.getsize(filepath)
                
                try:
                    text = extract_text(filepath)
                    parsed_data = parse_resume(text)
                    
                    score, breakdown, feedback = calculate_jd_match_score(parsed_data, jd_data)
                    missing_skills = analyze_skill_gap(parsed_data['skills'], jd.title)
                    
                    suggestions = {
                        'weaknesses': feedback,
                        'missing_keywords': missing_skills
                    }
                    
                    analysis_json = json.dumps({
                        'score': score,
                        'breakdown': breakdown,
                        'details': parsed_data,
                        'suggestions': suggestions,
                        'role': jd.title,
                    })

                    resume_entry = Resume(
                        user_id=current_user.id,
                        filename=file.filename,
                        filepath=safe_name,
                        file_size=file_size,
                        score=score,
                        role_applied=jd.title,
                        analysis_data=analysis_json,
                        job_id=jd.id,
                        applicant_status='New',
                        batch_id=batch_id
                    )
                    db.session.add(resume_entry)
                    db.session.flush()

                    ats_entry = AtsScore(
                        candidate_id=str(current_user.id),
                        job_id=str(jd.id),
                        resume_id=resume_entry.id,
                        resume_text=text[:10000],
                        score=score,
                        breakdown=breakdown,
                        missing_skills=missing_skills,
                        red_flags=feedback,
                        status='New'
                    )
                    ats_entry.save()

                    parsed_entry = ParsedData(
                        resume_id=resume_entry.id,
                        name=parsed_data.get('name'),
                        email=parsed_data.get('email'),
                        phone=parsed_data.get('phone'),
                        skills=json.dumps(parsed_data.get('skills', [])),
                        experience=json.dumps(parsed_data.get('experience', [])),
                        education=json.dumps(parsed_data.get('education', [])),
                        raw_text=text[:10000],
                    )
                    db.session.add(parsed_entry)
                    processed_count += 1
                except Exception as e:
                    print(f"Error processing {file.filename}: {e}")
                    
        db.session.commit()
        flash(f'Successfully processed {processed_count} resumes for {jd.title}', 'success')
        return redirect(url_for('admin.job_applicants', job_id=job_id))
        
    ats_scores = AtsScore.objects(job_id=str(job_id)).order_by('-score')
    applicants = []
    for ats in ats_scores:
        app = Resume.query.get(ats.resume_id)
        if app:
            app.score = ats.score
            app.applicant_status = ats.status
            app.data = ats.to_json()
            if app.analysis_data:
                app_json = json.loads(app.analysis_data)
                app.data['details'] = app_json.get('details', {})
            applicants.append(app)
            
    return render_template('applicants.html', job=jd, applicants=applicants)

@admin.route('/api/jobs/<int:job_id>/resumes/bulk', methods=['POST'])
@login_required
@recruiter_required
def api_bulk_upload_resumes(job_id):
    jd = JobDescription.query.get(job_id)
    if not jd:
        return jsonify({'error': 'Please select a valid job before uploading resumes. Job not found.'}), 404

    files = request.files.getlist('resumes')
    if not files or len(files) == 0 or files[0].filename == '':
        return jsonify({'error': 'No files provided.'}), 400

    if len(files) > 50:
        return jsonify({'error': 'Maximum 50 resumes allowed per bulk upload batch.'}), 400

    jd_data = {
        "required_skills": json.loads(jd.required_skills) if jd.required_skills else [],
        "nice_to_have_skills": json.loads(jd.nice_to_have_skills) if jd.nice_to_have_skills else [],
        "experience_level": jd.experience_level,
        "education_requirement": jd.education_requirement
    }

    results = []
    batch_id = str(uuid.uuid4())[:8]
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            results.append({"candidateName": file.filename, "score": 0, "status": "Failed (Only PDFs allowed)", "error": True})
            continue
            
        # Check file size (5MB = 5 * 1024 * 1024 bytes)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 5 * 1024 * 1024:
            results.append({"candidateName": file.filename, "score": 0, "status": "Failed (Exceeds 5MB limit)", "error": True})
            continue

        import secrets
        safe_name = secrets.token_hex(8) + '_' + file.filename
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_name)
        file.save(filepath)
        
        try:
            text = extract_text(filepath)
            parsed_data = parse_resume(text)
            
            score, breakdown, feedback = calculate_jd_match_score(parsed_data, jd_data)
            missing_skills = analyze_skill_gap(parsed_data['skills'], jd.title)
            
            suggestions = {
                'weaknesses': feedback,
                'missing_keywords': missing_skills
            }
            
            analysis_json = json.dumps({
                'score': score,
                'breakdown': breakdown,
                'details': parsed_data,
                'suggestions': suggestions,
                'role': jd.title,
            })

            resume_entry = Resume(
                user_id=current_user.id,
                filename=file.filename,
                filepath=safe_name,
                file_size=file_size,
                score=score,
                role_applied=jd.title,
                analysis_data=analysis_json,
                job_id=jd.id,
                applicant_status='New',
                batch_id=batch_id
            )
            db.session.add(resume_entry)
            db.session.flush()

            ats_entry = AtsScore(
                candidate_id=str(current_user.id),
                job_id=str(jd.id),
                resume_id=resume_entry.id,
                resume_text=text[:10000],
                score=score,
                breakdown=breakdown,
                missing_skills=missing_skills,
                red_flags=feedback,
                status='New'
            )
            ats_entry.save()

            parsed_entry = ParsedData(
                resume_id=resume_entry.id,
                name=parsed_data.get('name', 'Unknown Candidate'),
                email=parsed_data.get('email'),
                phone=parsed_data.get('phone'),
                skills=json.dumps(parsed_data.get('skills', [])),
                experience=json.dumps(parsed_data.get('experience', [])),
                education=json.dumps(parsed_data.get('education', [])),
                raw_text=text[:10000],
            )
            db.session.add(parsed_entry)
            db.session.commit()
            
            candidate_name = parsed_data.get('name') or file.filename
            results.append({
                "candidateName": candidate_name,
                "score": score,
                "status": "New",
                "error": False
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error processing {file.filename}: {e}")
            results.append({"candidateName": file.filename, "score": 0, "status": "Failed (Parsing error)", "error": True})
            
    return jsonify(results)

@admin.route('/applicants/<int:app_id>')
@login_required
@recruiter_required
def applicant_detail(app_id):
    resume = Resume.query.get_or_404(app_id)
    ats = AtsScore.objects(resume_id=app_id).first()
    
    data = {}
    if ats:
        resume.score = ats.score
        resume.applicant_status = ats.status
        resume.recruiter_notes = ats.recruiter_notes
        data = ats.to_json()
        if resume.analysis_data:
            data['details'] = json.loads(resume.analysis_data).get('details', {})
    return render_template('applicant_detail.html', resume=resume, data=data)

@admin.route('/applicants/<int:app_id>/status', methods=['POST'])
@login_required
@recruiter_required
def applicant_update_status(app_id):
    resume = Resume.query.get_or_404(app_id)
    ats = AtsScore.objects(resume_id=app_id).first()
    if not ats:
        flash('ATS Score mapping not found', 'error')
        return redirect(url_for('admin.applicant_detail', app_id=app_id))
        
    if 'status' in request.form:
        ats.status = request.form.get('status')
        # also update sqlite to keep conceptually in sync during migration phase
        resume.applicant_status = ats.status
    if 'notes' in request.form:
        ats.recruiter_notes = request.form.get('notes')
        resume.recruiter_notes = ats.recruiter_notes
        
    ats.save()
    db.session.commit()
    flash('Applicant updated', 'success')
    return redirect(url_for('admin.applicant_detail', app_id=app_id))

@admin.route('/shortlist')
@login_required
@recruiter_required
def shortlist():
    shortlisted_ats = AtsScore.objects(status='Shortlisted').order_by('-score')
    
    candidates = []
    for ats in shortlisted_ats:
        app = Resume.query.get(ats.resume_id)
        if app:
            app.score = ats.score
            app.applicant_status = ats.status
            app.data = ats.to_json()
            if app.analysis_data:
                app.data['details'] = json.loads(app.analysis_data).get('details', {})
            candidates.append(app)
            if len(candidates) >= 3:
                break
                
    return render_template('shortlist_compare.html', candidates=candidates)

