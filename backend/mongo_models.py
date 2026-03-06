from mongoengine import Document, StringField, IntField, DictField, ListField, DateTimeField
from datetime import datetime

class AtsScore(Document):
    """
    Mongoose Equivalent Schema for ATS Scores using Python MongoEngine
    """
    meta = {
        'collection': 'ats_scores',
        'indexes': [
            ('job_id', '-score')
        ]
    }

    candidate_id = StringField()          # link to User ID
    job_id = StringField()                # link to JobDescription ID
    resume_id = IntField()                # link to SQLite Resume Tracking
    
    resume_text = StringField()           # raw parsed resume
    score = IntField()                    # 0-100 overall score
    
    breakdown = DictField()               # skillsMatch, experienceMatch, educationMatch, niceToHaveMatch
    
    matched_skills = ListField(StringField())  # skills found in both JD and resume
    missing_skills = ListField(StringField())  # required skills not found in resume
    red_flags = ListField(StringField())       # e.g. "employment gap", "frequent job changes"
    
    status = StringField(choices=["New", "Shortlisted", "Hold", "Rejected"], default="New")
    recruiter_notes = StringField()
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    def to_json(self):
        return {
            "id": str(self.id),
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "resume_id": self.resume_id,
            "score": self.score,
            "breakdown": self.breakdown,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "red_flags": self.red_flags,
            "status": self.status,
            "recruiter_notes": self.recruiter_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
