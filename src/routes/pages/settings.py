from flask import Blueprint
from flask_inertia import render_inertia

from src.services.config import ConfigManager

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
def settings():
    return render_inertia(
        'Settings/Index',
        props={
            'settings': {
                'smtp': ConfigManager.get_all_masked('smtp'),
                'email': ConfigManager.get_all_masked('email'),
            }
        },
    )
