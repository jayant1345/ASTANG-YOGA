from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from app.models import User, RegistrationRequest
from app.utils import generate_password_reset_token, verify_password_reset_token
from app import db


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account is deactivated. Contact admin.', 'danger')
                return redirect(url_for('auth.login'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter_by(email=email).first():
            flash('This email is already registered. Please login.', 'danger')
            return render_template('auth/register.html', form=form)
        existing_req = RegistrationRequest.query.filter_by(
            email=email, status='pending'
        ).first()
        if existing_req:
            flash('A registration request with this email is already pending admin approval.', 'warning')
            return render_template('auth/register.html', form=form)
        req = RegistrationRequest(
            name=form.name.data.strip(),
            email=email,
            phone=form.phone.data,
            dob=form.dob.data,
            address=form.address.data,
            class_preference=form.class_preference.data,
            blood_group=form.blood_group.data or None,
            medical_condition=form.medical_condition.data or None,
        )
        req.set_password(form.password.data)
        db.session.add(req)
        db.session.commit()
        flash('Registration submitted! Admin will review and activate your account.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        # Always show success to avoid email enumeration
        flash('If that email is registered, contact your admin to get the reset link.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html', form=form)


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user_id, error = verify_password_reset_token(token)
    if error == 'expired':
        flash('This reset link has expired. Ask admin to generate a new one.', 'danger')
        return redirect(url_for('auth.login'))
    if error or not user_id:
        flash('Invalid reset link.', 'danger')
        return redirect(url_for('auth.login'))
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Password reset successfully. Please login.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
