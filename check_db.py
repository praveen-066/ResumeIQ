from app import create_app
from models import db, User

app = create_app()

def check():
    with app.app_context():
        users = User.query.all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f" - ID: {u.id}, Username: {u.username}, Email: {u.email}, Role: {u.role}")

if __name__ == '__main__':
    check()
