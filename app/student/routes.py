from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.student import bp
from app.models import Task, TaskSubmission, StudentClass, YogaClass, Attendance, ClassSession, CarouselSlide
from app.decorators import student_required
from app.utils import save_upload, allowed_file


@bp.route('/')
@login_required
@student_required
def dashboard():
    fee_statuses = current_user.get_all_fee_statuses()
    has_overdue = any(s and s['status'] == 'overdue' for s in fee_statuses)

    enrolled_classes = current_user.get_enrolled_classes()
    class_ids = [c.id for c in enrolled_classes]

    # Pending tasks count
    direct_tasks = Task.query.filter_by(assigned_to_student_id=current_user.id).all()
    class_tasks = (Task.query
                   .filter(Task.assigned_to_class_id.in_(class_ids))
                   .all()) if class_ids else []
    all_tasks = direct_tasks + class_tasks

    pending_count = 0
    for task in all_tasks:
        sub = TaskSubmission.query.filter_by(
            task_id=task.id, student_id=current_user.id
        ).first()
        if not sub or sub.status in ('pending', 'rejected'):
            pending_count += 1

    slides = (CarouselSlide.query
              .filter_by(is_active=True)
              .order_by(CarouselSlide.slide_order, CarouselSlide.id)
              .limit(5).all())

    total_attendance = Attendance.query.filter_by(student_id=current_user.id).count()

    return render_template('student/dashboard.html',
                           fee_statuses=fee_statuses,
                           has_overdue=has_overdue,
                           pending_count=pending_count,
                           enrolled_classes=enrolled_classes,
                           slides=slides,
                           total_attendance=total_attendance)


@bp.route('/tasks')
@login_required
@student_required
def tasks():
    enrolled_classes = current_user.get_enrolled_classes()
    class_ids = [c.id for c in enrolled_classes]

    direct_tasks = Task.query.filter_by(assigned_to_student_id=current_user.id).all()
    class_tasks = (Task.query
                   .filter(Task.assigned_to_class_id.in_(class_ids))
                   .all()) if class_ids else []
    all_tasks = list({t.id: t for t in direct_tasks + class_tasks}.values())

    task_data = []
    for task in sorted(all_tasks, key=lambda t: t.created_at, reverse=True):
        sub = TaskSubmission.query.filter_by(
            task_id=task.id, student_id=current_user.id
        ).first()
        task_data.append({'task': task, 'submission': sub})

    return render_template('student/tasks.html', task_data=task_data)


@bp.route('/tasks/<int:task_id>/submit', methods=['POST'])
@login_required
@student_required
def task_submit(task_id):
    task = Task.query.get_or_404(task_id)

    # Verify student is assigned
    enrolled_class_ids = [c.id for c in current_user.get_enrolled_classes()]
    is_assigned = (
        task.assigned_to_student_id == current_user.id or
        task.assigned_to_class_id in enrolled_class_ids
    )
    if not is_assigned:
        abort(403)

    sub = TaskSubmission.query.filter_by(
        task_id=task_id, student_id=current_user.id
    ).first()

    proof_path = None
    if 'proof' in request.files:
        file = request.files['proof']
        if file and file.filename and allowed_file(file.filename):
            proof_path = save_upload(file, 'proofs')

    if sub:
        sub.status = 'submitted'
        sub.submitted_at = datetime.utcnow()
        if proof_path:
            sub.proof_upload = proof_path
        sub.review_comment = None
    else:
        sub = TaskSubmission(
            task_id=task_id,
            student_id=current_user.id,
            status='submitted',
            submitted_at=datetime.utcnow(),
            proof_upload=proof_path,
        )
        db.session.add(sub)

    db.session.commit()
    flash('Task submitted for review.', 'success')
    return redirect(url_for('student.tasks'))
