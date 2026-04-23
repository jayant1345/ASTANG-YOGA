from datetime import datetime, date
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.instructor import bp
from app.instructor.forms import TaskForm, TaskReviewForm
from app.models import (YogaClass, ClassSession, Attendance,
                        StudentClass, User, Task, TaskSubmission)
from app.decorators import instructor_required
from app.utils import generate_session_token, generate_class_token, generate_qr_b64, now_ist


def _instructor_classes():
    if current_user.role == 'admin':
        return YogaClass.query.filter_by(is_active=True).all()
    return YogaClass.query.filter_by(
        instructor_id=current_user.id, is_active=True
    ).all()


@bp.route('/')
@login_required
@instructor_required
def dashboard():
    classes = _instructor_classes()
    today = date.today()

    class_data = []
    for yc in classes:
        active_session = yc.sessions.filter_by(is_active=True).first()
        today_sessions = yc.sessions.filter(
            db.func.date(ClassSession.started_at) == today
        ).all()
        today_count = sum(s.attendances.count() for s in today_sessions)
        enrolled_count = yc.enrollments.filter_by(is_active=True).count()
        class_data.append({
            'class': yc,
            'active_session': active_session,
            'today_count': today_count,
            'enrolled_count': enrolled_count,
        })

    return render_template('instructor/dashboard.html', class_data=class_data, today=today)


@bp.route('/session/start/<int:class_id>', methods=['POST'])
@login_required
@instructor_required
def session_start(class_id):
    yc = YogaClass.query.get_or_404(class_id)
    if current_user.role != 'admin' and yc.instructor_id != current_user.id:
        abort(403)

    existing = yc.sessions.filter_by(is_active=True).first()
    if existing:
        flash('A session is already active for this class.', 'warning')
        return redirect(url_for('instructor.session_live', session_id=existing.id))

    session_obj = ClassSession(
        class_id=class_id,
        instructor_id=current_user.id,
        started_at=now_ist(),
        is_active=True,
    )
    db.session.add(session_obj)
    db.session.flush()

    token = generate_session_token(session_obj.id)
    session_obj.signed_token = token
    db.session.commit()

    flash('Session started!', 'success')
    return redirect(url_for('instructor.session_live', session_id=session_obj.id))


@bp.route('/session/<int:session_id>/live')
@login_required
@instructor_required
def session_live(session_id):
    session_obj = ClassSession.query.get_or_404(session_id)
    yc = session_obj.yoga_class

    if current_user.role != 'admin' and yc.instructor_id != current_user.id:
        abort(403)

    class_token = generate_class_token(yc.id)
    verify_url = url_for('attendance.verify', class_token=class_token, _external=True)
    qr_b64 = generate_qr_b64(verify_url)

    enrolled = yc.get_enrolled_students()
    attendances = {a.student_id: a for a in session_obj.attendances.all()}

    rows = []
    for student in enrolled:
        att = attendances.get(student.id)
        fs = student.get_fee_status(yc.id)
        rows.append({'student': student, 'attendance': att, 'fee_status': fs})

    return render_template('instructor/live_session.html',
                           session_obj=session_obj,
                           yc=yc,
                           qr_b64=qr_b64,
                           rows=rows,
                           verify_url=verify_url)


@bp.route('/session/<int:session_id>/end', methods=['POST'])
@login_required
@instructor_required
def session_end(session_id):
    session_obj = ClassSession.query.get_or_404(session_id)
    yc = session_obj.yoga_class
    if current_user.role != 'admin' and yc.instructor_id != current_user.id:
        abort(403)

    session_obj.is_active = False
    session_obj.ended_at = now_ist()
    db.session.commit()
    flash('Session ended.', 'success')
    return redirect(url_for('instructor.dashboard'))


# ── Task Management ──────────────────────────────────────────────────────────

@bp.route('/tasks')
@login_required
@instructor_required
def tasks():
    classes = _instructor_classes()
    class_ids = [c.id for c in classes]
    student_ids_in_my_classes = (
        StudentClass.query
        .filter(StudentClass.class_id.in_(class_ids), StudentClass.is_active == True)
        .with_entities(StudentClass.student_id)
        .distinct()
        .all()
    )
    my_student_ids = [r[0] for r in student_ids_in_my_classes]

    my_tasks = (Task.query
                .filter(
                    db.or_(
                        Task.assigned_by_id == current_user.id,
                        Task.assigned_to_class_id.in_(class_ids),
                        Task.assigned_to_student_id.in_(my_student_ids)
                    )
                )
                .order_by(Task.created_at.desc())
                .all())
    return render_template('instructor/tasks.html', tasks=my_tasks)


@bp.route('/tasks/new', methods=['GET', 'POST'])
@login_required
@instructor_required
def task_new():
    form = TaskForm()
    classes = _instructor_classes()
    form.class_id.choices = [(0, '— Select Class —')] + [(c.id, c.name) for c in classes]

    all_students = []
    for c in classes:
        for s in c.get_enrolled_students():
            if not any(x[0] == s.id for x in all_students):
                all_students.append((s.id, f'{s.name} ({c.name})'))
    form.student_id.choices = [(0, '— Select Student —')] + all_students

    if form.validate_on_submit():
        task = Task(
            title=form.title.data.strip(),
            description=form.description.data,
            due_date=form.due_date.data,
            assigned_by_id=current_user.id,
        )
        if form.assign_to.data == 'class' and form.class_id.data:
            task.assigned_to_class_id = form.class_id.data
        elif form.assign_to.data == 'student' and form.student_id.data:
            task.assigned_to_student_id = form.student_id.data
        else:
            flash('Please select a class or student.', 'danger')
            return render_template('instructor/task_form.html', form=form)
        db.session.add(task)
        db.session.commit()
        flash('Task created.', 'success')
        return redirect(url_for('instructor.tasks'))
    return render_template('instructor/task_form.html', form=form)


@bp.route('/tasks/<int:task_id>/review', methods=['GET', 'POST'])
@login_required
@instructor_required
def task_review(task_id):
    task = Task.query.get_or_404(task_id)
    form = TaskReviewForm()

    student_id = request.args.get('student_id', type=int)
    submission = TaskSubmission.query.filter_by(
        task_id=task_id, student_id=student_id
    ).first_or_404() if student_id else None

    if not submission:
        submissions = task.submissions.all()
        return render_template('instructor/task_submissions.html', task=task, submissions=submissions)

    if form.validate_on_submit():
        submission.status = form.status.data
        submission.review_comment = form.review_comment.data
        submission.reviewed_by_id = current_user.id
        submission.reviewed_at = now_ist()
        db.session.commit()
        flash('Review submitted.', 'success')
        return redirect(url_for('instructor.tasks'))

    return render_template('instructor/task_review.html', task=task, submission=submission, form=form)
