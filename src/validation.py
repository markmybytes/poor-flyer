"""Request-body validation bridge: pydantic models plus one transport-aware error handler.

`@validated(Model)` parses the request body (JSON, else form), validates it, and puts
the model on `g.validated`. A single `ValidationError` handler then dispatches by
blueprint: page writes redirect back with the session error bag, API writes answer
422 with the envelope from STYLE.md.

Form-encoded bodies cannot express `flights[]`; a create posted as a form has no legs
and fails the schema's min-1 rule (Inertia always posts JSON).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any
from urllib.parse import urlsplit

from flask import g, jsonify, redirect, request, session
from flask.typing import ResponseReturnValue
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

API_BLUEPRINT_PREFIX = 'api.'


def _payload() -> dict[str, Any]:
    body = request.get_json(silent=True) or request.form.to_dict()
    return body if isinstance(body, dict) else {}


def validated(
    model: type[BaseModel],
    *,
    error_key: str | None = None,
    error_copy: str | None = None,
    redirect_to: str | None = None,
) -> Callable:
    """Validate the request body into `model` before the view runs.

    `error_key` collapses every failure onto one bag key (otherwise each field keeps
    its own); `error_copy` fixes that collapsed message; `redirect_to` is the page
    fallback when the request has no usable same-origin referrer.
    """

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            g.validation_error_key = error_key
            g.validation_error_copy = error_copy
            g.validation_redirect = redirect_to.format(**kwargs) if redirect_to else None
            g.validated = model.model_validate(_payload())
            return view(*args, **kwargs)

        return wrapper

    return decorator


def _flatten(error: ValidationError) -> dict[str, list[str]]:
    """Map pydantic errors to field-keyed messages; a nested path folds onto its first key."""
    fields: dict[str, list[str]] = {}
    for item in error.errors():
        loc = [part for part in item['loc'] if part != 'body']
        field = str(loc[0]) if loc else 'request'
        # ValueError copies are wrapped as "Value error, ..."; the original lives in ctx
        message = item.get('ctx', {}).get('error') or item['msg']
        fields.setdefault(field, []).append(str(message))
    return fields


def back_url(fallback: str | None = None) -> str:
    """Land a page error on the page that sent it, never on another origin."""
    referrer = request.referrer
    if referrer:
        parts = urlsplit(referrer)
        same_origin = parts.scheme in ('', 'http', 'https') and parts.netloc in ('', request.host)
        if same_origin and parts.path.startswith('/') and not parts.path.startswith(('//', '/\\')):
            return f'{parts.path}?{parts.query}' if parts.query else parts.path
    return fallback or request.path


def _is_api_request() -> bool:
    return (request.blueprint or '').startswith(API_BLUEPRINT_PREFIX) or request.path.startswith(
        '/api/'
    )


def handle_validation_error(error: ValidationError) -> ResponseReturnValue:
    errors = _flatten(error)
    if _is_api_request():
        logger.info('rejected api payload: fields=%s', ','.join(errors))
        return jsonify({'message': 'Validation failed', 'data': None, 'errors': errors}), 422

    key = g.get('validation_error_key')
    copy = g.get('validation_error_copy')
    if key:
        session['errors'] = {key: copy or next(iter(errors.values()))[0]}
    else:
        session['errors'] = {field: messages[0] for field, messages in errors.items()}
    logger.info('rejected page payload: fields=%s', ','.join(errors))
    return redirect(back_url(g.get('validation_redirect')))
