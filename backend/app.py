import os
import secrets
from dotenv import load_dotenv

# Load .env from the server/ directory (where this file lives)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate

# ---------------------------------------------------------------------------
from models import db          # single shared SQLAlchemy instance
from mongo_db import init_mongodb

login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()


def create_app():
    # Point Flask at the client/ folder for templates and static files
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CLIENT_DIR = os.path.join(BASE_DIR, '..', 'frontend')

    app = Flask(
        __name__,
        template_folder=os.path.join(CLIENT_DIR, 'templates'),
        static_folder=os.path.join(CLIENT_DIR, 'static'),
    )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY', 'dev-secret-key-resumeiq-do-not-use-in-prod'
    )

    # File uploads — stored inside server/uploads/
    app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

    # Database — SQLite stored inside server/instance/
    db_path = os.path.join(BASE_DIR, 'instance', 'resumeiq.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        os.environ.get('DATABASE_URL') or f'sqlite:///{db_path}'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # OpenRouter AI scoring — key loaded from .env (never hardcoded)
    app.config['OPENROUTER_API_KEY'] = os.environ.get('OPENROUTER_API_KEY', '')

    # Recommended pool settings for SQLite; safe for other engines too.
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
    }

    # ------------------------------------------------------------------
    # Ensure required directories exist
    # ------------------------------------------------------------------
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

    # ------------------------------------------------------------------
    # Initialise extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)        # Flask-Migrate (Alembic)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    init_mongodb(app)                # Connect to MongoDB via MongoEngine

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # ------------------------------------------------------------------
    # User loader for Flask-Login
    # ------------------------------------------------------------------
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ------------------------------------------------------------------
    # Register Blueprints
    # ------------------------------------------------------------------
    from routes.auth import auth as auth_blueprint
    from routes.main import main as main_blueprint
    from routes.admin import admin as admin_blueprint

    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(main_blueprint)
    app.register_blueprint(admin_blueprint)

    # ------------------------------------------------------------------
    # Create tables & seed default admin (only on first run)
    # ------------------------------------------------------------------
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username='admin').first():
            hashed_pw = bcrypt.generate_password_hash('password123').decode('utf-8')
            admin_user = User(
                username='admin',
                email='admin@gmail.com',
                password=hashed_pw,
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print('[DB] Default admin user created (username=admin, password=password123)')

    return app
