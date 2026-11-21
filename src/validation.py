"""Request-body validation bridge: pydantic models plus one transport-aware rejection.

`@validated(Model)` parses the request body (JSON, else form), validates it, and puts
the model on `g.validated`. Both validation failures — pydantic's `ValidationError` and
the domain `InvalidFieldsError` — dispatch by blueprint: page writes redirect back with
the session error bag, API writes answer 422 with the envelope from STYLE.md.

Field keys keep the full dotted `loc` path (`flights.0.origin`), so a page bag holds
one plain string per failing field and an API body one string array per key.

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

from src.services.errors import InvalidFieldsError

logger = logging.getLogger(__name__)

API_BLUEPRINT_PREFIX = 'api.'


# pydantic owns these templates; a validator's copy arrives in ctx and wins.
GENERIC_MESSAGES = {
    'missing': '必填欄位',
    'extra_forbidden': '不允許的欄位',
    'too_short': '請至少填寫一項',
}


def _payload() -> dict[str, Any]:
    body = request.get_json(silent=True) or request.form.to_dict()
    return body if isinstance(body, dict) else {}


def validated(
    model: type[BaseModel],
    *,
    redirect_to: str | None = None,
) -> Callable[[Callable[..., ResponseReturnValue]], Callable[..., ResponseReturnValue]]:
    """Validate the request body into `model` before the view runs.

    `redirect_to` is the page fallback when the request has no usable same-origin
    referrer; every failure keeps its own field key.
    """

    def decorator(view: Callable[..., ResponseReturnValue]) -> Callable[..., ResponseReturnValue]:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> ResponseReturnValue:
            g.validation_redirect = redirect_to.format(**kwargs) if redirect_to else None
            g.validated = model.model_validate(_payload())
            return view(*args, **kwargs)

        return wrapper

    return decorator


def _flatten(error: ValidationError) -> dict[str, list[str]]:
    """Map pydantic errors to full dotted field keys, keeping every message.

    An unknown-key error is model-level (`loc == ()`), so the schema reports the
    offending names in `ctx['fields']`; split them back into per-field keys.
    """
    fields: dict[str, list[str]] = {}
    for item in error.errors():
        ctx = item.get('ctx') or {}
        if item['type'] == 'unsupported_field':
            for field in str(ctx['fields']).split(', '):
                fields.setdefault(field, []).append(f'不允許的欄位：{field}')
            continue

        fields.setdefault(
            '.'.join(
                str(part)
                for part in ([part for part in item['loc'] if part not in ('body', 'query')])
            )
            or 'request',
            [],
        ).append(str(ctx.get('error') or GENERIC_MESSAGES.get(item['type'], '格式不正確')))
    return fields


def back_url(fallback: str | None = None) -> str:
    """Land a page error on the page that sent it, never on another origin."""
    if request.referrer:
        parts = urlsplit(request.referrer)
        same_origin = parts.scheme in ('', 'http', 'https') and parts.netloc in ('', request.host)
        if same_origin and parts.path.startswith('/') and not parts.path.startswith(('//', '/\\')):
            return f'{parts.path}?{parts.query}' if parts.query else parts.path
    return fallback or request.path


def _is_api_request() -> bool:
    return (request.blueprint or '').startswith(API_BLUEPRINT_PREFIX) or request.path.startswith(
        '/api/'
    )


def _reject(errors: dict[str, list[str]]) -> ResponseReturnValue:
    """Answer either transport from one field-to-messages map."""
    if _is_api_request():
        logger.info('rejected api payload: fields=%s', ','.join(errors))
        return jsonify({'message': '驗證失敗', 'data': None, 'errors': errors}), 422

    session['errors'] = {field: messages[0] for field, messages in errors.items()}
    logger.info('rejected page payload: fields=%s', ','.join(errors))
    return redirect(back_url(g.get('validation_redirect')))


def handle_validation_error(error: ValidationError) -> ResponseReturnValue:
    return _reject(_flatten(error))


def handle_invalid_fields(error: InvalidFieldsError) -> ResponseReturnValue:
    return _reject({issue.field: [issue.message] for issue in error.errors})
