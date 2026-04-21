from functools import wraps
from flask import abort, render_template
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated


def instructor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('admin', 'instructor'):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            abort(403)
        return f(*args, **kwargs)
    return decorated


def fees_clear_required(f):
    """
    Use on routes that accept class_id as a URL kwarg or query param.
    Blocks access and renders blocked page if the student's fee is overdue.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request
        class_id = kwargs.get('class_id') or request.args.get('class_id')
        if class_id and current_user.is_authenticated and current_user.role == 'student':
            fee_status = current_user.get_fee_status(int(class_id))
            if fee_status and fee_status['status'] == 'overdue':
                return render_template('attendance/blocked.html', fee_status=fee_status), 403
        return f(*args, **kwargs)
    return decorated
