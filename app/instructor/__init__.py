from flask import Blueprint

bp = Blueprint('instructor', __name__, template_folder='../../templates/instructor')

from app.instructor import routes  # noqa: F401, E402
