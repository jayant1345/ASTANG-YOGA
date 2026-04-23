from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.attendance import bp
from app.models import ClassSession, Attendance, StudentClass, YogaClass
from app.utils import verify_class_token, generate_class_token, generate_qr_b64


@bp.route('/scan')
@login_required
def scan():
    return render_template('attendance/scan.html')


@bp.route('/class/<int:class_id>/display')
def class_display(class_id):
    """Full-screen / printable QR page — no login required so it can run on a wall tablet."""
    yc = YogaClass.query.get_or_404(class_id)
    class_token = generate_class_token(yc.id)
    verify_url = url_for('attendance.verify', class_token=class_token, _external=True)
    qr_b64 = generate_qr_b64(verify_url)
    active_session = yc.sessions.filter_by(is_active=True).first()
    return render_template('attendance/class_display.html',
                           yc=yc, qr_b64=qr_b64, active_session=active_session)


@bp.route('/verify')
@login_required
def verify():
    """Handles class-based permanent QR codes."""
    class_token = request.args.get('class_token', '')
    if not class_token:
        flash('Invalid QR code.', 'danger')
        return redirect(url_for('attendance.scan'))

    class_id, error = verify_class_token(class_token)
    if error or not class_id:
        flash('Invalid QR code.', 'danger')
        return redirect(url_for('attendance.scan'))

    yc = YogaClass.query.get(class_id)
    if not yc:
        flash('Class not found.', 'danger')
        return redirect(url_for('attendance.scan'))

    session_obj = yc.sessions.filter_by(is_active=True).first()
    if not session_obj:
        if not yc.is_active:
            flash(f'{yc.name} is not currently active. Contact admin.', 'warning')
            return redirect(url_for('student.dashboard'))
        # Auto-create today's session on first scan
        session_obj = ClassSession(
            class_id=yc.id,
            instructor_id=yc.instructor_id,
            is_active=True,
        )
        db.session.add(session_obj)
        db.session.flush()  # get session_obj.id before commit

    if current_user.role == 'student':
        enrollment = StudentClass.query.filter_by(
            student_id=current_user.id, class_id=yc.id, is_active=True
        ).first()
        if not enrollment:
            flash(f'You are not enrolled in {yc.name}.', 'danger')
            return redirect(url_for('student.dashboard'))

        fee_status = current_user.get_fee_status(yc.id)
        if fee_status and fee_status['status'] == 'overdue':
            return render_template('attendance/blocked.html', fee_status=fee_status), 403

    existing = Attendance.query.filter_by(
        student_id=current_user.id, session_id=session_obj.id
    ).first()
    if existing:
        return render_template('attendance/success.html',
                               session_obj=session_obj, yc=yc,
                               status=existing.status, already_marked=True)

    elapsed = (datetime.utcnow() - session_obj.started_at).total_seconds() / 60
    late_threshold = current_app.config.get('LATE_THRESHOLD_MINUTES', 10)
    status = 'late' if elapsed > late_threshold else 'present'

    att = Attendance(
        student_id=current_user.id,
        session_id=session_obj.id,
        status=status,
        timestamp=datetime.utcnow()
    )
    db.session.add(att)
    db.session.commit()

    return render_template('attendance/success.html',
                           session_obj=session_obj, yc=yc,
                           status=status, already_marked=False)
