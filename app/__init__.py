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

    with app.app_context():
        db.create_all()
        _auto_create_admin()
        _auto_seed_classes()

    return app


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


def _auto_seed_classes():
    """Seed the 9 default yoga batch classes if none exist."""
    from app.models import User, YogaClass
    if YogaClass.query.first():
        return
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        return
    classes = [
        ('Morning 06:15 Batch', '06:15 AM', 'Main Hall', 2500.0),
        ('Morning 07:15 Batch', '07:15 AM', 'Main Hall', 2500.0),
        ('Morning 08:15 Batch', '08:15 AM', 'Main Hall', 2500.0),
        ('Morning 09:15 Batch', '09:15 AM', 'Main Hall', 2500.0),
        ('Morning 10:15 Batch', '10:15 AM', 'Main Hall', 2500.0),
        ('Morning 11:15 Batch', '11:15 AM', 'Main Hall', 2500.0),
        ('Evening 05:15 Batch', '05:15 PM', 'Main Hall', 2500.0),
        ('Evening 06:15 Batch', '06:15 PM', 'Main Hall', 2500.0),
        ('Evening 07:15 Batch', '07:15 PM', 'Main Hall', 2500.0),
    ]
    for name, time, location, fee in classes:
        db.session.add(YogaClass(
            name=name, schedule_time=time,
            location=location, monthly_fee_amount=fee,
            instructor_id=admin.id,
        ))
    db.session.commit()
