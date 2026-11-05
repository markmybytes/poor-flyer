"""Static reference lookups for form pickers."""

from flask import Blueprint, jsonify
from fli.models.airline import AIRLINE_NAMES

from src.extensions.cache import cache

lookup_bp = Blueprint('lookup', __name__, url_prefix='/airlines')


@cache.cached(timeout=86400, key_prefix='airline:names:v1')
def _airline_options() -> list[dict[str, str]]:
    """IATA code/name pairs, digit-leading enum keys normalized (``_7C`` -> ``7C``)."""
    return sorted(
        ({'code': code.removeprefix('_'), 'name': name} for code, name in AIRLINE_NAMES.items()),
        key=lambda airline: airline['code'],
    )


@lookup_bp.route('', methods=['GET'])
def list_airlines():
    return jsonify({'message': None, 'data': _airline_options()})
