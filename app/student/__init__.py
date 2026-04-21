from flask import Blueprint

bp = Blueprint('student', __name__, template_folder='../../templates/student')

from app.student import routes  # noqa: F401, E402
