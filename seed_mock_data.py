from app import create_app
from models import db, User, Resume, ParsedData
from flask_bcrypt import Bcrypt
import json

app = create_app()
bcrypt = Bcrypt()

def seed_data():
    with app.app_context():
        # Clear existing non-admin data if any
        User.query.filter(User.username != 'admin').delete()
        Resume.query.delete()
        
        # Create a mock user
        user = User(username='candidate_one', email='one@example.com', password=bcrypt.generate_password_hash('pass').decode('utf-8'))
        db.session.add(user)
        db.session.commit()
        
        # Create some mock resumes with different scores and roles
        resumes_data = [
            {'filename': 'john_frontend.pdf', 'role': 'Frontend Developer', 'score': 92},
            {'filename': 'jane_backend.pdf', 'role': 'Backend Developer', 'score': 85},
            {'filename': 'bob_devops.pdf', 'role': 'DevOps Engineer', 'score': 78},
            {'filename': 'alice_ds.pdf', 'role': 'Data Scientist', 'score': 95},
            {'filename': 'charlie_fe.pdf', 'role': 'Frontend Developer', 'score': 82},
        ]
        
        for data in resumes_data:
            resume = Resume(
                user_id=user.id,
                filename=data['filename'],
                role_applied=data['role'],
                score=data['score'],
                analysis_data=json.dumps({"summary": "Great candidate"})
            )
            db.session.add(resume)
        
        db.session.commit()
        print("Mock data seeded successfully!")

if __name__ == '__main__':
    seed_data()
