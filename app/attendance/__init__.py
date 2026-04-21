from flask import Blueprint

bp = Blueprint('attendance', __name__, template_folder='../../templates/attendance')

from app.attendance import routes  # noqa: F401, E402
