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

    return app
