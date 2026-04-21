from flask import Blueprint

bp = Blueprint('tasks', __name__, template_folder='../../templates/tasks')

from app.tasks import routes  # noqa: F401, E402
