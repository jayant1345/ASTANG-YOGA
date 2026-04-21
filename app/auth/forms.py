from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField,
                     DateField, TextAreaField)
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
