from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, SelectField, FloatField,
                     SubmitField, TextAreaField, DateField, BooleanField)
from wtforms.validators import DataRequired, Email, Optional, Length, NumberRange


class UserForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    role = SelectField('Role', choices=[
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
    ], validators=[DataRequired()])
    password = PasswordField('Password (leave blank to keep existing)')
    is_active = BooleanField('Active', default=True)
    profile_photo = FileField('Profile Photo', validators=[
        Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only')
    ])
    blood_group = SelectField('Blood Group',
                              choices=[('', '— Select —'),
                                       ('A+', 'A+'), ('A-', 'A-'),
                                       ('B+', 'B+'), ('B-', 'B-'),
                                       ('AB+', 'AB+'), ('AB-', 'AB-'),
                                       ('O+', 'O+'), ('O-', 'O-'),
                                       ('Unknown', 'Unknown')],
                              validate_choice=False)
    medical_condition = TextAreaField('Medical Conditions', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Save User')


class YogaClassForm(FlaskForm):
    name = StringField('Class Name', validators=[DataRequired(), Length(max=100)])
    instructor_id = SelectField('Instructor', coerce=int, validators=[DataRequired()])
    schedule_time = StringField('Schedule', validators=[Optional(), Length(max=100)],
                                description='e.g. Mon/Wed/Fri 7:00 AM')
    location = StringField('Location', validators=[Optional(), Length(max=200)])
    monthly_fee_amount = FloatField('Monthly Fee (₹)', validators=[
        DataRequired(), NumberRange(min=0)
    ])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Class')


class EnrollStudentForm(FlaskForm):
    student_id = SelectField('Student', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Enroll Student')


class FeeRecordForm(FlaskForm):
    student_id = SelectField('Student', coerce=int, validators=[DataRequired()])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount (₹)', validators=[DataRequired(), NumberRange(min=0)])
    paid_for_month = StringField('Month (YYYY-MM)', validators=[DataRequired(), Length(min=7, max=7)],
                                 description='e.g. 2026-04')
    payment_date = DateField('Payment Date', validators=[DataRequired()])
    method_note = SelectField('Payment Method', choices=[
        ('cash', 'Cash'), ('upi', 'UPI'), ('bank_transfer', 'Bank Transfer'), ('other', 'Other')
    ])
    remarks = TextAreaField('Remarks', validators=[Optional()])
    submit = SubmitField('Record Payment')


class CarouselSlideForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    body = TextAreaField('Write-up / Caption', validators=[Optional()])
    image = FileField('Photo', validators=[
        Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only')
    ])
    slide_order = StringField('Order (lower = first)', validators=[Optional()])
    is_active = BooleanField('Show on student page', default=True)
    submit = SubmitField('Save Slide')


class AttendanceOverrideForm(FlaskForm):
    student_id = SelectField('Student', coerce=int, validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('present', 'Present'), ('late', 'Late'), ('absent', 'Absent')
    ])
    submit = SubmitField('Save')
