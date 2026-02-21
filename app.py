import os
import sys
import secrets
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate

# ---------------------------------------------------------------------------
# Extension instances — created here so blueprints can import them directly.
# ---------------------------------------------------------------------------
from models import db          # single shared SQLAlchemy instance

login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()


def create_app():
    # Detect if we are running in a bundled PyInstaller environment
    if getattr(sys, 'frozen', False):
        template_folder = os.path.join(sys._MEIPASS, 'templates')
        static_folder = os.path.join(sys._MEIPASS, 'static')
        app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    else:
        app = Flask(__name__)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    
    # Detect Environment
    is_vercel = os.environ.get('VERCEL') == '1'
    is_frozen = getattr(sys, 'frozen', False)

    if is_vercel:
        # Vercel Environment (Cloud)
        app_data_path = os.getcwd() 
        upload_path = '/tmp/uploads'
        db_uri = f'sqlite:///{os.path.join(app_data_path, "resumeiq.db")}'
        print("Running in Cloud (Vercel) mode")
    elif is_frozen:
        # Desktop Bundle Environment (.exe)
        app_data_path = os.path.join(os.path.expanduser('~'), 'Documents', 'ResumeIQ_Data')
        upload_path = os.path.join(app_data_path, 'uploads')
        db_uri = f'sqlite:///{os.path.join(app_data_path, "resumeiq.db")}'
        print(f"Running in Desktop (Frozen) mode. Data at: {app_data_path}")
    else:
        # Standard Development Environment
        app_data_path = app.instance_path
        upload_path = os.path.join(app.root_path, 'uploads')
        db_uri = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(app_data_path, "resumeiq.db")}'
        print("Running in Development mode")

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-resumeiq-do-not-use-in-prod')
    app.config['UPLOAD_FOLDER'] = upload_path
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
    }

    # ------------------------------------------------------------------
    # Ensure required directories exist
    # ------------------------------------------------------------------
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # ------------------------------------------------------------------
    # Initialise extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)        # Flask-Migrate (Alembic)
    login_manager.init_app(app)
    bcrypt.init_app(app)

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


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, use_reloader=False)
