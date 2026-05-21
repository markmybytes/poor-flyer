from flask import Blueprint
from flask_inertia import render_inertia

from src.services import config

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
def index():
    return render_inertia(
        'Settings/Index',
        props={
            'settings': {
                'smtp': config.get_all_masked('smtp'),
                'email': config.get_all_masked('email'),
            }
        },
    )
