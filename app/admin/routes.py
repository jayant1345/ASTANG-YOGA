from datetime import date, datetime
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.admin import bp
from app.admin.forms import (UserForm, YogaClassForm, EnrollStudentForm,
                              FeeRecordForm, AttendanceOverrideForm, CarouselSlideForm)
from app.models import (User, YogaClass, StudentClass, ClassSession,
                        Attendance, FeeRecord, RegistrationRequest, CarouselSlide)
from app.decorators import admin_required
from app.utils import (save_upload, export_csv_response,
                       generate_password_reset_token, generate_class_token, generate_qr_b64)


@bp.route('/')
@login_required
@admin_required
def dashboard():
    pending_registrations = RegistrationRequest.query.filter_by(status='pending').count()
    total_students = User.query.filter_by(role='student', is_active=True).count()
    today = date.today()

    today_sessions = ClassSession.query.filter(
        db.func.date(ClassSession.started_at) == today
    ).all()
    today_session_ids = [s.id for s in today_sessions]
    today_present = 0
    if today_session_ids:
        today_present = (Attendance.query
                         .filter(Attendance.session_id.in_(today_session_ids),
                                 Attendance.status.in_(['present', 'late']))
                         .with_entities(Attendance.student_id)
                         .distinct()
                         .count())

    enrolled_today = (StudentClass.query
                      .join(YogaClass, YogaClass.id == StudentClass.class_id)
                      .filter(StudentClass.is_active == True)
                      .with_entities(StudentClass.student_id)
                      .distinct()
                      .count())

    attendance_pct = round((today_present / enrolled_today * 100) if enrolled_today else 0, 1)

    total_fee_collected = db.session.query(
        db.func.coalesce(db.func.sum(FeeRecord.amount), 0)
    ).scalar()

    active_sessions = ClassSession.query.filter_by(is_active=True).all()

    slides = (CarouselSlide.query
              .filter_by(is_active=True)
              .order_by(CarouselSlide.slide_order, CarouselSlide.id)
              .limit(5).all())

    return render_template('admin/dashboard.html',
                           total_students=total_students,
                           attendance_pct=attendance_pct,
                           total_fee_collected=total_fee_collected,
                           active_sessions=active_sessions,
                           pending_registrations=pending_registrations,
                           today=today,
                           slides=slides)


# ── User Management ──────────────────────────────────────────────────────────

@bp.route('/users')
@login_required
@admin_required
def users():
    role_filter = request.args.get('role', '')
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    all_users = query.order_by(User.name).all()
    return render_template('admin/users.html', users=all_users, role_filter=role_filter)


@bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def user_new():
    form = UserForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash('Email already registered.', 'danger')
            return render_template('admin/user_form.html', form=form, title='New User')
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data,
            role=form.role.data,
            is_active=form.is_active.data,
        )
        if form.password.data:
            user.set_password(form.password.data)
        else:
            flash('Password is required for new users.', 'danger')
            return render_template('admin/user_form.html', form=form, title='New User')
        if form.profile_photo.data and form.profile_photo.data.filename:
            user.profile_photo = save_upload(form.profile_photo.data, 'profiles')
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.name} created.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title='New User')


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if existing and existing.id != user.id:
            flash('Email already used by another account.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Edit User', user=user)
        user.name = form.name.data.strip()
        user.email = form.email.data.lower().strip()
        user.phone = form.phone.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        if form.profile_photo.data and form.profile_photo.data.filename:
            user.profile_photo = save_upload(form.profile_photo.data, 'profiles')
        db.session.commit()
        flash(f'User {user.name} updated.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title='Edit User', user=user)


@bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def user_toggle(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        state = 'activated' if user.is_active else 'deactivated'
        flash(f'User {user.name} {state}.', 'success')
    return redirect(url_for('admin.users'))


# ── Class Management ─────────────────────────────────────────────────────────

@bp.route('/classes')
@login_required
@admin_required
def classes():
    all_classes = sorted(
        YogaClass.query.all(),
        key=lambda c: (0 if 'Morning' in (c.name or '') else 1, c.schedule_time or '')
    )
    return render_template('admin/classes.html', classes=all_classes)


@bp.route('/classes/new', methods=['GET', 'POST'])
@login_required
@admin_required
def class_new():
    form = YogaClassForm()
    form.instructor_id.choices = [
        (u.id, u.name) for u in User.query.filter_by(role='instructor', is_active=True).all()
    ]
    if form.validate_on_submit():
        yc = YogaClass(
            name=form.name.data.strip(),
            instructor_id=form.instructor_id.data,
            schedule_time=form.schedule_time.data,
            location=form.location.data,
            monthly_fee_amount=form.monthly_fee_amount.data,
            is_active=form.is_active.data,
        )
        db.session.add(yc)
        db.session.commit()
        flash(f'Class "{yc.name}" created.', 'success')
        return redirect(url_for('admin.classes'))
    return render_template('admin/class_form.html', form=form, title='New Class')


@bp.route('/classes/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def class_edit(class_id):
    yc = YogaClass.query.get_or_404(class_id)
    form = YogaClassForm(obj=yc)
    form.instructor_id.choices = [
        (u.id, u.name) for u in User.query.filter_by(role='instructor', is_active=True).all()
    ]
    if form.validate_on_submit():
        yc.name = form.name.data.strip()
        yc.instructor_id = form.instructor_id.data
        yc.schedule_time = form.schedule_time.data
        yc.location = form.location.data
        yc.monthly_fee_amount = form.monthly_fee_amount.data
        yc.is_active = form.is_active.data
        db.session.commit()
        flash(f'Class "{yc.name}" updated.', 'success')
        return redirect(url_for('admin.classes'))
    return render_template('admin/class_form.html', form=form, title='Edit Class', yc=yc)


@bp.route('/classes/<int:class_id>/delete', methods=['POST'])
@login_required
@admin_required
def class_delete(class_id):
    yc = YogaClass.query.get_or_404(class_id)
    if yc.enrollments.filter_by(is_active=True).count() > 0:
        flash('Cannot delete a class with active enrolled students.', 'danger')
        return redirect(url_for('admin.classes'))
    db.session.delete(yc)
    db.session.commit()
    flash(f'Class "{yc.name}" deleted.', 'success')
    return redirect(url_for('admin.classes'))


@bp.route('/classes/<int:class_id>/enroll', methods=['GET', 'POST'])
@login_required
@admin_required
def class_enroll(class_id):
    yc = YogaClass.query.get_or_404(class_id)
    form = EnrollStudentForm()
    enrolled_ids = [e.student_id for e in yc.enrollments.filter_by(is_active=True).all()]
    available = User.query.filter(
        User.role == 'student',
        User.is_active == True,
        ~User.id.in_(enrolled_ids)
    ).order_by(User.name).all()
    form.student_id.choices = [(u.id, f'{u.name} ({u.email})') for u in available]

    if form.validate_on_submit():
        existing = StudentClass.query.filter_by(
            student_id=form.student_id.data, class_id=class_id
        ).first()
        if existing:
            existing.is_active = True
        else:
            enrollment = StudentClass(
                student_id=form.student_id.data,
                class_id=class_id,
                joined_date=date.today()
            )
            db.session.add(enrollment)
        db.session.commit()
        flash('Student enrolled.', 'success')
        return redirect(url_for('admin.class_enroll', class_id=class_id))

    enrollments = (StudentClass.query
                   .filter_by(class_id=class_id, is_active=True)
                   .join(User, User.id == StudentClass.student_id)
                   .order_by(User.name)
                   .all())
    return render_template('admin/enroll.html', yc=yc, form=form, enrollments=enrollments)


@bp.route('/classes/<int:class_id>/unenroll/<int:student_id>', methods=['POST'])
@login_required
@admin_required
def class_unenroll(class_id, student_id):
    enrollment = StudentClass.query.filter_by(
        class_id=class_id, student_id=student_id
    ).first_or_404()
    enrollment.is_active = False
    db.session.commit()
    flash('Student unenrolled.', 'success')
    return redirect(url_for('admin.class_enroll', class_id=class_id))


# ── Fee Management ───────────────────────────────────────────────────────────

@bp.route('/fees')
@login_required
@admin_required
def fees():
    class_filter = request.args.get('class_id', type=int)
    status_filter = request.args.get('status', '')

    students = User.query.filter_by(role='student', is_active=True).order_by(User.name).all()
    classes = YogaClass.query.filter_by(is_active=True).order_by(YogaClass.name).all()

    defaulters = []
    for student in students:
        for cls in (YogaClass.query.get(class_filter),) if class_filter else classes:
            if cls is None:
                continue
            fs = student.get_fee_status(cls.id)
            if fs and (not status_filter or fs['status'] == status_filter):
                defaulters.append({'student': student, 'fee_status': fs})

    records = FeeRecord.query.order_by(FeeRecord.payment_date.desc()).limit(50).all()
    return render_template('admin/fees.html',
                           defaulters=defaulters,
                           records=records,
                           classes=classes,
                           class_filter=class_filter,
                           status_filter=status_filter)


@bp.route('/fees/record', methods=['GET', 'POST'])
@login_required
@admin_required
def fee_record():
    form = FeeRecordForm()
    students = User.query.filter_by(role='student', is_active=True).order_by(User.name).all()
    classes = YogaClass.query.filter_by(is_active=True).order_by(YogaClass.name).all()
    form.student_id.choices = [(u.id, f'{u.name} ({u.email})') for u in students]
    form.class_id.choices = [(c.id, c.name) for c in classes]

    if request.method == 'GET':
        from datetime import date
        form.payment_date.data = date.today()
        form.paid_for_month.data = date.today().strftime('%Y-%m')

    if form.validate_on_submit():
        rec = FeeRecord(
            student_id=form.student_id.data,
            class_id=form.class_id.data,
            amount=form.amount.data,
            paid_for_month=form.paid_for_month.data,
            payment_date=form.payment_date.data,
            method_note=form.method_note.data,
            recorded_by_admin_id=current_user.id,
            remarks=form.remarks.data,
        )
        db.session.add(rec)
        db.session.commit()
        flash('Fee payment recorded.', 'success')
        return redirect(url_for('admin.fees'))
    return render_template('admin/fee_record_form.html', form=form)


@bp.route('/fees/export')
@login_required
@admin_required
def fees_export():
    records = FeeRecord.query.order_by(FeeRecord.payment_date.desc()).all()
    headers = ['Student', 'Email', 'Class', 'Month', 'Amount', 'Payment Date', 'Method', 'Remarks']
    rows = [[
        r.student.name, r.student.email, r.yoga_class.name,
        r.paid_for_month, r.amount, r.payment_date, r.method_note, r.remarks or ''
    ] for r in records]
    return export_csv_response(headers, rows, 'fee_records.csv')


# ── Attendance Management ────────────────────────────────────────────────────

@bp.route('/attendance')
@login_required
@admin_required
def attendance():
    class_filter = request.args.get('class_id', type=int)
    date_filter = request.args.get('date', date.today().isoformat())

    try:
        filter_date = date.fromisoformat(date_filter)
    except ValueError:
        filter_date = date.today()

    sessions_q = ClassSession.query.filter(
        db.func.date(ClassSession.started_at) == filter_date
    )
    if class_filter:
        sessions_q = sessions_q.filter_by(class_id=class_filter)
    sessions = sessions_q.order_by(ClassSession.started_at.desc()).all()
    classes = YogaClass.query.filter_by(is_active=True).order_by(YogaClass.name).all()

    return render_template('admin/attendance.html',
                           sessions=sessions,
                           classes=classes,
                           class_filter=class_filter,
                           date_filter=date_filter)


@bp.route('/attendance/session/<int:session_id>')
@login_required
@admin_required
def attendance_session(session_id):
    session_obj = ClassSession.query.get_or_404(session_id)
    yc = session_obj.yoga_class
    enrolled = yc.get_enrolled_students()
    attendances = {a.student_id: a for a in session_obj.attendances.all()}

    rows = []
    for student in enrolled:
        att = attendances.get(student.id)
        fs = student.get_fee_status(yc.id)
        rows.append({'student': student, 'attendance': att, 'fee_status': fs})

    return render_template('admin/attendance_session.html',
                           session_obj=session_obj,
                           yc=yc,
                           rows=rows)


@bp.route('/attendance/session/<int:session_id>/mark/<int:student_id>', methods=['POST'])
@login_required
@admin_required
def attendance_mark(session_id, student_id):
    session_obj = ClassSession.query.get_or_404(session_id)
    status = request.form.get('status', 'present')

    att = Attendance.query.filter_by(
        student_id=student_id, session_id=session_id
    ).first()
    if att:
        att.status = status
        att.overridden_by_admin = True
    else:
        att = Attendance(
            student_id=student_id,
            session_id=session_id,
            status=status,
            overridden_by_admin=True,
            timestamp=datetime.utcnow()
        )
        db.session.add(att)
    db.session.commit()
    flash('Attendance updated.', 'success')
    return redirect(url_for('admin.attendance_session', session_id=session_id))


@bp.route('/attendance/export')
@login_required
@admin_required
def attendance_export():
    class_filter = request.args.get('class_id', type=int)
    date_filter = request.args.get('date', '')

    query = (Attendance.query
             .join(ClassSession, ClassSession.id == Attendance.session_id)
             .join(YogaClass, YogaClass.id == ClassSession.class_id)
             .join(User, User.id == Attendance.student_id))

    if class_filter:
        query = query.filter(ClassSession.class_id == class_filter)
    if date_filter:
        try:
            fd = date.fromisoformat(date_filter)
            query = query.filter(db.func.date(ClassSession.started_at) == fd)
        except ValueError:
            pass

    records = query.order_by(ClassSession.started_at.desc()).all()
    headers = ['Date', 'Class', 'Student', 'Email', 'Status', 'Timestamp', 'Admin Override']
    rows = [[
        a.session.started_at.strftime('%Y-%m-%d'),
        a.session.yoga_class.name,
        a.student.name,
        a.student.email,
        a.status,
        a.timestamp.strftime('%H:%M:%S'),
        'Yes' if a.overridden_by_admin else 'No'
    ] for a in records]
    return export_csv_response(headers, rows, 'attendance.csv')


# ── Student Registration Requests ─────────────────────────────────────────────

@bp.route('/registrations')
@login_required
@admin_required
def registrations():
    status_filter = request.args.get('status', 'pending')
    query = RegistrationRequest.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    reqs = query.order_by(RegistrationRequest.created_at.desc()).all()
    return render_template('admin/registrations.html', reqs=reqs, status_filter=status_filter)


@bp.route('/registrations/<int:req_id>/approve', methods=['POST'])
@login_required
@admin_required
def registration_approve(req_id):
    reg = RegistrationRequest.query.get_or_404(req_id)
    if reg.status != 'pending':
        flash('Request already processed.', 'warning')
        return redirect(url_for('admin.registrations'))
    if User.query.filter_by(email=reg.email).first():
        flash('A user with this email already exists.', 'danger')
        reg.status = 'rejected'
        reg.reject_reason = 'Email already registered'
        reg.reviewed_at = datetime.utcnow()
        reg.reviewed_by_id = current_user.id
        db.session.commit()
        return redirect(url_for('admin.registrations'))
    user = User(
        name=reg.name,
        email=reg.email,
        phone=reg.phone,
        role='student',
        is_active=True,
        password_hash=reg.password_hash,
    )
    db.session.add(user)
    reg.status = 'approved'
    reg.reviewed_at = datetime.utcnow()
    reg.reviewed_by_id = current_user.id
    db.session.commit()
    flash(f'"{reg.name}" approved and account created.', 'success')
    return redirect(url_for('admin.registrations'))


@bp.route('/registrations/<int:req_id>/reject', methods=['POST'])
@login_required
@admin_required
def registration_reject(req_id):
    reg = RegistrationRequest.query.get_or_404(req_id)
    if reg.status != 'pending':
        flash('Request already processed.', 'warning')
        return redirect(url_for('admin.registrations'))
    reason = request.form.get('reason', '').strip()
    reg.status = 'rejected'
    reg.reject_reason = reason
    reg.reviewed_at = datetime.utcnow()
    reg.reviewed_by_id = current_user.id
    db.session.commit()
    flash(f'Registration for "{reg.name}" rejected.', 'info')
    return redirect(url_for('admin.registrations'))


# ── Password Reset Link ────────────────────────────────────────────────────────

@bp.route('/users/<int:user_id>/reset-link')
@login_required
@admin_required
def user_reset_link(user_id):
    user = User.query.get_or_404(user_id)
    token = generate_password_reset_token(user.id)
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    return render_template('admin/reset_link.html', user=user, reset_url=reset_url)


# ── Registration QR Code ───────────────────────────────────────────────────────

@bp.route('/registration-qr')
@login_required
@admin_required
def registration_qr():
    register_url = url_for('auth.register', _external=True)
    qr_b64 = generate_qr_b64(register_url)
    return render_template('admin/registration_qr.html', qr_b64=qr_b64, register_url=register_url)


# ── Per-class Attendance QR ───────────────────────────────────────────────────

@bp.route('/classes/<int:class_id>/qr')
@login_required
@admin_required
def class_qr(class_id):
    yc = YogaClass.query.get_or_404(class_id)
    class_token = generate_class_token(yc.id)
    verify_url = url_for('attendance.verify', class_token=class_token, _external=True)
    qr_b64 = generate_qr_b64(verify_url)
    return render_template('admin/class_qr.html', yc=yc, qr_b64=qr_b64, verify_url=verify_url)


# ── Carousel Slides ───────────────────────────────────────────────────────────

@bp.route('/carousel')
@login_required
@admin_required
def carousel():
    slides = CarouselSlide.query.order_by(CarouselSlide.slide_order, CarouselSlide.id).all()
    return render_template('admin/carousel.html', slides=slides)


@bp.route('/carousel/new', methods=['GET', 'POST'])
@login_required
@admin_required
def carousel_new():
    form = CarouselSlideForm()
    if form.validate_on_submit():
        slide = CarouselSlide(
            title=form.title.data.strip(),
            body=form.body.data,
            slide_order=int(form.slide_order.data or 0),
            is_active=form.is_active.data,
        )
        if form.image.data and form.image.data.filename:
            slide.image_path = save_upload(form.image.data, 'slides')
        db.session.add(slide)
        db.session.commit()
        flash('Slide added.', 'success')
        return redirect(url_for('admin.carousel'))
    return render_template('admin/carousel_form.html', form=form, title='New Slide', slide=None)


@bp.route('/carousel/<int:slide_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def carousel_edit(slide_id):
    slide = CarouselSlide.query.get_or_404(slide_id)
    form = CarouselSlideForm(obj=slide)
    if form.validate_on_submit():
        slide.title = form.title.data.strip()
        slide.body = form.body.data
        slide.slide_order = int(form.slide_order.data or 0)
        slide.is_active = form.is_active.data
        if form.image.data and form.image.data.filename:
            slide.image_path = save_upload(form.image.data, 'slides')
        db.session.commit()
        flash('Slide updated.', 'success')
        return redirect(url_for('admin.carousel'))
    form.slide_order.data = str(slide.slide_order)
    return render_template('admin/carousel_form.html', form=form, title='Edit Slide', slide=slide)


@bp.route('/carousel/<int:slide_id>/delete', methods=['POST'])
@login_required
@admin_required
def carousel_delete(slide_id):
    slide = CarouselSlide.query.get_or_404(slide_id)
    db.session.delete(slide)
    db.session.commit()
    flash('Slide deleted.', 'success')
    return redirect(url_for('admin.carousel'))
