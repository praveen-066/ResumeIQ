from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for
from flask_login import login_required, current_user
import os
import json
import secrets
import hashlib

from models import db, Resume, ParsedData, Inquiry
from utils.extractor import extract_text
from utils.scorer import calculate_ats_score
from utils.analyzer import parse_resume, analyze_skill_gap
from utils.decorators import candidate_required
from mongo_models import AtsScore
main = Blueprint('main', __name__)


@main.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
        
    try:
        from utils.constants import TARGET_ROLES
        target_roles = TARGET_ROLES
    except ImportError:
        target_roles = {
            "Software Development": ["Frontend Developer", "Backend Developer", "Full Stack Developer", "Software Engineer"],
            "Data & AI": ["Data Scientist", "Data Engineer", "Machine Learning Engineer"],
            "Cloud & DevOps": ["DevOps Engineer", "Cloud Architect"],
            "Design & Product": ["UI/UX Designer", "Product Manager"],
            "Cybersecurity": ["Cybersecurity Analyst", "Security Engineer"],
            "Testing": ["QA Engineer", "Automation Test Engineer"],
        }
    return render_template('index.html', target_roles=target_roles, is_authenticated=current_user.is_authenticated, user_role=current_user.role if current_user.is_authenticated else None)



@main.route('/upload', methods=['POST'])
@login_required
@candidate_required
def upload_file():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['resume']
    target_role = request.form.get('role', 'Frontend Developer')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    allowed = file.filename.lower().endswith(('.pdf', '.docx'))
    if not (file and allowed):
        return jsonify({'error': 'Invalid file type. Only PDF and DOCX allowed.'}), 400

    # Save the uploaded file
    safe_name = secrets.token_hex(8) + '_' + file.filename
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], safe_name)
    file.save(filepath)
    file_size = os.path.getsize(filepath)

    try:
        # --- Extract text ---
        text = extract_text(filepath)

        # ── Deduplication: SHA-256 of normalised text ────────────────────────
        # If this user has already submitted the same resume for the same role,
        # return the stored result immediately — no LLM call, no variance.
        content_hash = hashlib.sha256(text.strip().lower().encode()).hexdigest()
        cached_resume = Resume.query.filter_by(
            user_id=current_user.id,
            role_applied=target_role,
            content_hash=content_hash,
        ).order_by(Resume.created_at.desc()).first()

        if cached_resume and cached_resume.analysis_data:
            cached_result = json.loads(cached_resume.analysis_data)
            cached_result['cached'] = True
            return jsonify(cached_result)

        # ── Full pipeline (first-time upload) ───────────────────────────────
        parsed_data = parse_resume(text)
        score, breakdown, feedback = calculate_ats_score(parsed_data, target_role)
        missing_skills = analyze_skill_gap(parsed_data['skills'], target_role)
        
        # ── AI-powered feedback via OpenRouter ──────────────────────────────
        from utils.ai_scorer import get_ai_feedback
        from utils.analyzer import generate_ai_tips
        api_key = current_app.config.get('OPENROUTER_API_KEY', '')
        ai_result = get_ai_feedback(
            resume_text=parsed_data.get('text', ''),
            target_role=target_role,
            score=score,
            breakdown=breakdown,
            missing_skills=missing_skills,
            api_key=api_key,
        )

        # Use AI tips when available, fall back to rule-based tips
        if ai_result.get('ai_powered') and ai_result.get('tips'):
            dynamic_tips = ai_result['tips']
        else:
            dynamic_tips = generate_ai_tips(parsed_data)

        suggestions = {
            'strengths': ([f"Found {len(parsed_data['skills'])} relevant skills."]
                          if parsed_data['skills'] else []),
            'weaknesses': feedback,
            'missing_keywords': missing_skills,
            'improvements': dynamic_tips,
            'ai_narrative': ai_result.get('narrative', ''),
            'ai_powered': ai_result.get('ai_powered', False),
        }
        if score > 80:
            suggestions['strengths'].append('Great ATS score!')

        analysis_json = json.dumps({
            'score': score,
            'breakdown': breakdown,
            'details': parsed_data,
            'suggestions': suggestions,
            'role': target_role,
        })

        # --- Persist Resume record ---
        resume_entry = Resume(
            user_id=current_user.id,
            filename=file.filename,
            filepath=safe_name,          # relative path inside uploads/
            file_size=file_size,
            score=score,
            role_applied=target_role,
            analysis_data=analysis_json,
            content_hash=content_hash,   # store for future deduplication
        )
        db.session.add(resume_entry)
        db.session.flush()               # get resume_entry.id before committing

        ats_score = AtsScore(
            candidate_id=str(current_user.id),
            resume_id=resume_entry.id,
            resume_text=text[:10000],
            score=score,
            breakdown=breakdown,
            missing_skills=missing_skills,
            red_flags=feedback,
            status="New"
        )
        ats_score.save()

        # --- Persist ParsedData record ---
        parsed_entry = ParsedData(
            resume_id=resume_entry.id,
            name=parsed_data.get('name'),
            email=parsed_data.get('email'),
            phone=parsed_data.get('phone'),
            skills=json.dumps(parsed_data.get('skills', [])),
            experience=json.dumps(parsed_data.get('experience', [])),
            education=json.dumps(parsed_data.get('education', [])),
            raw_text=text[:10000],       # cap to avoid huge text blobs
        )
        db.session.add(parsed_entry)
        db.session.commit()

        return jsonify({
            'score': score,
            'breakdown': breakdown,
            'details': parsed_data,
            'suggestions': suggestions,
            'role': target_role,
            'cached': False,
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@main.route('/result')
@login_required
@candidate_required
def result():
    return render_template('result.html')


@main.route('/report/<int:resume_id>')
@login_required
def view_report(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    
    # Check permission: Owner, Recruiter, or Admin can view
    if current_user.role not in ['admin', 'recruiter'] and resume.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    analysis_data = json.loads(resume.analysis_data) if resume.analysis_data else {}
    return render_template('result.html', resume=resume, data=analysis_data)


@main.route('/dashboard')
@login_required
@candidate_required
def dashboard():
    resumes = (
        Resume.query
        .filter_by(user_id=current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )
    for r in resumes:
        mongo_score = AtsScore.objects(resume_id=r.id).first()
        if mongo_score:
            r.score = mongo_score.score
            r.data = mongo_score.to_json()
            if r.analysis_data:
                r.data['details'] = json.loads(r.analysis_data).get('details', {})
        elif r.analysis_data:
            r.data = json.loads(r.analysis_data)
    return render_template('dashboard.html', resumes=resumes)


@main.route('/api/contact', methods=['POST'])
def contact():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    name = data.get('name')
    email = data.get('email')
    subject = data.get('subject')
    message = data.get('message')
    
    if not all([name, email, subject, message]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    try:
        new_inquiry = Inquiry(name=name, email=email, subject=subject, message=message)
        db.session.add(new_inquiry)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Message sent successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
