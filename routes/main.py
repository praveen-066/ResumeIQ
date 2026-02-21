from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
import os
import json
import secrets

from models import db, Resume, ParsedData
from utils.extractor import extract_text
from utils.scorer import calculate_ats_score
from utils.analyzer import parse_resume, analyze_skill_gap

main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/upload', methods=['POST'])
@login_required
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
        # --- Extract & analyse ---
        text = extract_text(filepath)
        parsed_data = parse_resume(text)
        score, breakdown, feedback = calculate_ats_score(parsed_data)
        missing_skills = analyze_skill_gap(parsed_data['skills'], target_role)
        
        # Dynamic AI Tips
        from utils.analyzer import generate_ai_tips
        dynamic_tips = generate_ai_tips(parsed_data)

        suggestions = {
            'strengths': ([f"Found {len(parsed_data['skills'])} relevant skills."]
                          if parsed_data['skills'] else []),
            'weaknesses': feedback,
            'missing_keywords': missing_skills,
            'improvements': dynamic_tips,
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
        )
        db.session.add(resume_entry)
        db.session.flush()               # get resume_entry.id before committing

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
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@main.route('/result')
@login_required
def result():
    return render_template('result.html')


@main.route('/dashboard')
@login_required
def dashboard():
    resumes = (
        Resume.query
        .filter_by(user_id=current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )
    for r in resumes:
        if r.analysis_data:
            r.data = json.loads(r.analysis_data)
    return render_template('dashboard.html', resumes=resumes)
