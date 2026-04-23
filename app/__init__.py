import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'  # resolves to /auth/login
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.auth import bp as auth_bp
    from app.admin import bp as admin_bp
    from app.instructor import bp as instructor_bp
    from app.student import bp as student_bp
    from app.attendance import bp as attendance_bp
    from app.tasks import bp as tasks_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(instructor_bp, url_prefix='/instructor')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')

    @app.before_request
    def check_user_active():
        from flask import redirect, url_for, flash
        if current_user.is_authenticated and not current_user.is_active:
            logout_user()
            flash('Your account has been deactivated. Contact admin.', 'danger')
            return redirect(url_for('auth.login'))

    @app.route('/login')
    def login_redirect():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))

    @app.route('/')
    def index():
        from flask import redirect, url_for
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        if current_user.role == 'instructor':
            return redirect(url_for('instructor.dashboard'))
        return redirect(url_for('student.dashboard'))

    def _media_url(path):
        """Return a usable URL for an uploaded file.
        Cloudinary uploads store full https:// URLs; local uploads store relative paths."""
        if not path:
            return ''
        if path.startswith(('http://', 'https://')):
            return path
        from flask import url_for
        return url_for('static', filename=path)

    app.jinja_env.globals['media_url'] = _media_url

    with app.app_context():
        db.create_all()
        _run_migrations()
        _auto_create_admin()

    return app


def _run_migrations():
    """Add new columns to existing tables when deploying to an existing database.
    Uses IF NOT EXISTS so it is safe to run on every startup."""
    migrations = [
        "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS blood_group VARCHAR(10)",
        "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS medical_condition TEXT",
        "ALTER TABLE registration_request ADD COLUMN IF NOT EXISTS blood_group VARCHAR(10)",
        "ALTER TABLE registration_request ADD COLUMN IF NOT EXISTS medical_condition TEXT",
    ]
    try:
        with db.engine.connect() as conn:
            for sql in migrations:
                conn.execute(db.text(sql))
            conn.commit()
    except Exception:
        pass  # SQLite doesn't support IF NOT EXISTS for ADD COLUMN — db.create_all() handles it


def _auto_create_admin():
    """Auto-create admin on first deploy using ADMIN_EMAIL / ADMIN_PASSWORD env vars."""
    import os
    from app.models import User
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if not admin_email or not admin_password:
        return
    if User.query.filter_by(role='admin').first():
        return
    admin = User(
        name=os.environ.get('ADMIN_NAME', 'Super Admin'),
        email=admin_email,
        role='admin',
        is_active=True,
    )
    admin.set_password(admin_password)
    db.session.add(admin)
    db.session.commit()
