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


class Resume(db.Model):
    __tablename__ = 'resume'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Original file information
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=True)   # path inside uploads/
    file_size = db.Column(db.Integer, nullable=True)       # bytes

    # Analysis results
    score = db.Column(db.Integer, nullable=False)
    role_applied = db.Column(db.String(100), nullable=False)
    analysis_data = db.Column(db.Text, nullable=True)      # full JSON blob

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Resume id={self.id} file={self.filename!r} score={self.score}>'


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
