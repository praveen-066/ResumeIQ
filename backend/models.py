from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Cascade delete: removing a user also removes their resumes
    resumes = db.relationship(
        'Resume',
        backref='owner',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<User {self.username!r} role={self.role!r}>'


class JobDescription(db.Model):
    __tablename__ = 'job_description'

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(150), nullable=True)
    status = db.Column(db.String(20), default='Active', nullable=False)  # Active, Closed
    
    required_skills = db.Column(db.Text, nullable=True)  # JSON serialized
    nice_to_have_skills = db.Column(db.Text, nullable=True)  # JSON serialized
    experience_level = db.Column(db.Integer, nullable=True)  # years required
    education_requirement = db.Column(db.String(100), nullable=True)
    raw_text = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # A Job can have many Resumes (applicants)
    resumes = db.relationship('Resume', backref='job', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<JobDescription id={self.id} title={self.title!r}>'
class Resume(db.Model):
    __tablename__ = 'resume'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Original file information
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=True)   # path inside uploads/
    file_size = db.Column(db.Integer, nullable=True)       # bytes

    # Content fingerprint: SHA-256 of the normalised extracted text.
    # Used to detect duplicate uploads and serve cached results.
    content_hash = db.Column(db.String(64), nullable=True, index=True)

    # Analysis results
    score = db.Column(db.Integer, nullable=False)
    role_applied = db.Column(db.String(100), nullable=False)
    analysis_data = db.Column(db.Text, nullable=True)      # full JSON blob
    
    # Recruiter applicant tracking
    job_id = db.Column(db.Integer, db.ForeignKey('job_description.id'), nullable=True)
    applicant_status = db.Column(db.String(50), default='New', nullable=False) # New, Shortlisted, Hold, Rejected
    recruiter_notes = db.Column(db.Text, nullable=True)
    
    batch_id = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Resume id={self.id} file={self.filename!r} score={self.score} status={self.applicant_status}>'


class SMTPConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server = db.Column(db.String(150), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)
    use_tls = db.Column(db.Boolean, default=True)


class ParsedData(db.Model):
    """Stores the raw structured parse of a resume separately from the score."""
    __tablename__ = 'parsed_data'

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(
        db.Integer,
        db.ForeignKey('resume.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )

    # Individual parsed fields for querying / analytics
    name = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(254), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    skills = db.Column(db.Text, nullable=True)        # JSON list
    experience = db.Column(db.Text, nullable=True)    # JSON list
    education = db.Column(db.Text, nullable=True)     # JSON list
    raw_text = db.Column(db.Text, nullable=True)      # full extracted text

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    resume = db.relationship('Resume', backref=db.backref('parsed', uselist=False, cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<ParsedData resume_id={self.resume_id} name={self.name!r}>'


class Inquiry(db.Model):
    __tablename__ = 'inquiry'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='New')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Inquiry id={self.id} from={self.email!r} subject={self.subject!r}>'
