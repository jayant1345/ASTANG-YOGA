from datetime import datetime, date
import calendar
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, instructor, student
    profile_photo = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship('StudentClass', foreign_keys='StudentClass.student_id',
                                  backref='student', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_enrolled_classes(self):
        return (YogaClass.query
                .join(StudentClass, StudentClass.class_id == YogaClass.id)
                .filter(StudentClass.student_id == self.id, StudentClass.is_active == True)
                .all())

    def get_fee_status(self, class_id):
        today = date.today()
        current_month = today.strftime('%Y-%m')

        yoga_class = YogaClass.query.get(class_id)
        if not yoga_class:
            return None

        enrollment = StudentClass.query.filter_by(
            student_id=self.id, class_id=class_id, is_active=True
        ).first()
        if not enrollment:
            return None

        latest_fee = (FeeRecord.query
                      .filter_by(student_id=self.id, class_id=class_id)
                      .order_by(FeeRecord.paid_for_month.desc())
                      .first())

        if latest_fee and latest_fee.paid_for_month >= current_month:
            return {
                'status': 'paid',
                'due_month': None,
                'due_month_display': None,
                'amount': yoga_class.monthly_fee_amount,
                'days_overdue': 0,
                'class_name': yoga_class.name,
                'class_id': class_id,
            }

        day_of_month = today.day
        grace_period = current_app.config.get('GRACE_PERIOD_DAYS', 5)

        # Only go overdue if the student has paid before but missed this month.
        # A student with no payment history at all is always pending (not overdue).
        if latest_fee is None:
            status = 'pending'
            days_overdue = 0
        elif day_of_month <= grace_period:
            status = 'pending'
            days_overdue = 0
        else:
            status = 'overdue'
            days_overdue = day_of_month - grace_period

        year, month = current_month.split('-')
        month_display = f"{calendar.month_name[int(month)]} {year}"

        return {
            'status': status,
            'due_month': current_month,
            'due_month_display': month_display,
            'amount': yoga_class.monthly_fee_amount,
            'days_overdue': days_overdue,
            'class_name': yoga_class.name,
            'class_id': class_id,
        }

    def get_all_fee_statuses(self):
        return [self.get_fee_status(c.id) for c in self.get_enrolled_classes()]

    def has_overdue_fees(self):
        return any(s and s['status'] == 'overdue' for s in self.get_all_fee_statuses())

    def __repr__(self):
        return f'<User {self.email}>'


class YogaClass(db.Model):
    __tablename__ = 'yoga_class'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    schedule_time = db.Column(db.String(100))
    location = db.Column(db.String(200))
    monthly_fee_amount = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    instructor = db.relationship('User', foreign_keys=[instructor_id],
                                 backref=db.backref('taught_classes', lazy='dynamic'))
    enrollments = db.relationship('StudentClass', foreign_keys='StudentClass.class_id',
                                  backref='yoga_class', lazy='dynamic')
    sessions = db.relationship('ClassSession', backref='yoga_class', lazy='dynamic')

    def get_enrolled_students(self):
        return (User.query
                .join(StudentClass, StudentClass.student_id == User.id)
                .filter(StudentClass.class_id == self.id, StudentClass.is_active == True)
                .all())

    def __repr__(self):
        return f'<YogaClass {self.name}>'


class StudentClass(db.Model):
    __tablename__ = 'student_class'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('yoga_class.id'), nullable=False)
    joined_date = db.Column(db.Date, default=date.today)
    is_active = db.Column(db.Boolean, default=True)

    __table_args__ = (db.UniqueConstraint('student_id', 'class_id', name='uq_student_class'),)


class ClassSession(db.Model):
    __tablename__ = 'class_session'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('yoga_class.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    signed_token = db.Column(db.String(500), unique=True)

    instructor = db.relationship('User', foreign_keys=[instructor_id])
    attendances = db.relationship('Attendance', backref='session', lazy='dynamic')

    @property
    def duration_minutes(self):
        end = self.ended_at or datetime.utcnow()
        return int((end - self.started_at).total_seconds() / 60)


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('class_session.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='present')  # present, late, absent
    overridden_by_admin = db.Column(db.Boolean, default=False)

    student = db.relationship('User', foreign_keys=[student_id])

    __table_args__ = (db.UniqueConstraint('student_id', 'session_id', name='uq_attendance'),)


class FeeRecord(db.Model):
    __tablename__ = 'fee_record'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('yoga_class.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_for_month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    payment_date = db.Column(db.Date, default=date.today)
    method_note = db.Column(db.String(100))  # cash / upi / etc.
    recorded_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    remarks = db.Column(db.Text)

    student = db.relationship('User', foreign_keys=[student_id])
    yoga_class = db.relationship('YogaClass', foreign_keys=[class_id])
    recorded_by = db.relationship('User', foreign_keys=[recorded_by_admin_id])


class RegistrationRequest(db.Model):
    __tablename__ = 'registration_request'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    dob = db.Column(db.Date, nullable=False)
    address = db.Column(db.Text)
    class_preference = db.Column(db.String(200))
    password_hash = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reject_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)


class Task(db.Model):
    __tablename__ = 'task'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_to_student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_to_class_id = db.Column(db.Integer, db.ForeignKey('yoga_class.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id])
    assigned_to_student = db.relationship('User', foreign_keys=[assigned_to_student_id])
    assigned_to_class = db.relationship('YogaClass', foreign_keys=[assigned_to_class_id])
    submissions = db.relationship('TaskSubmission', backref='task', lazy='dynamic')


class CarouselSlide(db.Model):
    __tablename__ = 'carousel_slide'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    slide_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TaskSubmission(db.Model):
    __tablename__ = 'task_submission'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, submitted, approved, rejected
    proof_upload = db.Column(db.String(255))
    review_comment = db.Column(db.Text)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submitted_at = db.Column(db.DateTime)
    reviewed_at = db.Column(db.DateTime)

    student = db.relationship('User', foreign_keys=[student_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])

    __table_args__ = (db.UniqueConstraint('task_id', 'student_id', name='uq_task_submission'),)
