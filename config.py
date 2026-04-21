import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Railway provides postgres:// but SQLAlchemy requires postgresql://
    _db_url = os.environ.get('DATABASE_URL') or 'sqlite:///astang_yoga.db'
    SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GRACE_PERIOD_DAYS = int(os.environ.get('GRACE_PERIOD_DAYS', 5))
    SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 15))
    LATE_THRESHOLD_MINUTES = int(os.environ.get('LATE_THRESHOLD_MINUTES', 10))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')

    @staticmethod
    def init_app(app):
        base = Config.UPLOAD_FOLDER
        for sub in ('profiles', 'proofs', 'qrcodes'):
            os.makedirs(os.path.join(base, sub), exist_ok=True)
