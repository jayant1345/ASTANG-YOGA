from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField,
                     DateField, TextAreaField, SelectField)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(2, 100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(7, 20)])
    dob = DateField('Date of Birth', validators=[DataRequired()])
    address = TextAreaField('Address', validators=[Optional(), Length(max=300)])
    class_preference = StringField('Preferred Class / Batch Time',
                                   validators=[Optional(), Length(max=200)])
    blood_group = SelectField('Blood Group', validators=[Optional()],
                              choices=[('', '— Select —'),
                                       ('A+', 'A+'), ('A-', 'A-'),
                                       ('B+', 'B+'), ('B-', 'B-'),
                                       ('AB+', 'AB+'), ('AB-', 'AB-'),
                                       ('O+', 'O+'), ('O-', 'O-'),
                                       ('Unknown', 'Unknown / Not Sure')])
    medical_condition = TextAreaField('Medical Conditions / Health Notes',
                                      validators=[Optional(), Length(max=1000)],
                                      description='e.g. BP, back pain, knee surgery, diabetes…')
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=8,
                             message='Password must be at least 8 characters')])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(),
                                     EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Submit Registration')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password',
                             validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(),
                                     EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Reset Password')
