import os
import io
import base64
import csv
from datetime import datetime
from flask import current_app, make_response
from itsdangerous import (URLSafeTimedSerializer, URLSafeSerializer,
                          SignatureExpired, BadSignature)
import qrcode
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file, subfolder):
    if current_app.config.get('CLOUDINARY_URL'):
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(cloudinary_url=current_app.config['CLOUDINARY_URL'])
        result = cloudinary.uploader.upload(
            file,
            folder=f'astang_yoga/{subfolder}',
            resource_type='auto',
        )
        return result['secure_url']

    filename = secure_filename(file.filename)
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    filename = f"{ts}_{filename}"
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, filename))
    return f"uploads/{subfolder}/{filename}"


# ── Session token (kept for backward compat) ──────────────────────────────────

def generate_session_token(session_id):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps({'session_id': session_id}, salt='attendance-qr')


def verify_session_token(token):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    max_age = current_app.config.get('SESSION_TIMEOUT_MINUTES', 15) * 60
    try:
        data = s.loads(token, salt='attendance-qr', max_age=max_age)
        return data.get('session_id'), None
    except SignatureExpired:
        return None, 'expired'
    except BadSignature:
        return None, 'invalid'


# ── Per-class permanent attendance token ──────────────────────────────────────

def generate_class_token(class_id):
    """Permanent, signed token for a yoga class's attendance QR."""
    s = URLSafeSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(class_id, salt='class-attendance')


def verify_class_token(token):
    s = URLSafeSerializer(current_app.config['SECRET_KEY'])
    try:
        class_id = s.loads(token, salt='class-attendance')
        return class_id, None
    except BadSignature:
        return None, 'invalid'


# ── Password reset token (24h expiry) ─────────────────────────────────────────

def generate_password_reset_token(user_id):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(user_id, salt='password-reset')


def verify_password_reset_token(token, max_age=86400):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token, salt='password-reset', max_age=max_age)
        return user_id, None
    except SignatureExpired:
        return None, 'expired'
    except BadSignature:
        return None, 'invalid'


# ── QR code ───────────────────────────────────────────────────────────────────

def generate_qr_b64(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def export_csv_response(headers, rows, filename):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response
