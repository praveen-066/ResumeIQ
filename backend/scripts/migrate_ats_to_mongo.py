import os
import sys
import json
from datetime import datetime

# Add the parent directory to sys.path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Resume
from mongo_models import AtsScore

app = create_app()

def run_migration():
    with app.app_context():
        resumes = Resume.query.all()
        print(f"[*] Found {len(resumes)} records in SQLite Resume table.")
        
        success = 0
        failure = 0
        skipped = 0
        
        for r in resumes:
            # Check if this resume already has an AtsScore
            if AtsScore.objects(resume_id=r.id).first():
                skipped += 1
                continue
                
            try:
                if not r.analysis_data:
                    print(f"[!] Skipping Resume {r.id}: No analysis_data found.")
                    skipped += 1
                    continue
                    
                data = json.loads(r.analysis_data)
                
                sugg = data.get('suggestions', {})
                breakdown = data.get('breakdown', {})
                missing_skills = sugg.get('missing_keywords', [])
                red_flags = sugg.get('weaknesses', [])
                
                ats_score = AtsScore(
                    candidate_id=str(r.user_id),
                    job_id=str(r.job_id) if r.job_id else None,
                    resume_id=r.id,
                    score=r.score,
                    breakdown=breakdown,
                    missing_skills=missing_skills,
                    red_flags=red_flags,
                    status=r.applicant_status or "New",
                    recruiter_notes=r.recruiter_notes
                )
                ats_score.save()
                success += 1
                print(f"[+] Successfully migrated Resume ID {r.id} -> ATS Score ID {ats_score.id}")
            except Exception as e:
                failure += 1
                print(f"[-] Failed to migrate Resume ID {r.id}: {e}")
                
        print("\n" + "="*40)
        print(f"Migration Complete")
        print(f"Success: {success}")
        print(f"Failure: {failure}")
        print(f"Skipped: {skipped}")
        print("="*40)

if __name__ == '__main__':
    run_migration()
