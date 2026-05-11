from dataclasses import asdict, is_dataclass
from datetime import date, datetime

from flask.json.provider import DefaultJSONProvider


def to_camel(snake_str):
    """Converts snake_case to camelCase."""
    parts = snake_str.split("_")
    return parts[0] + "".join(x.title() for x in parts[1:])


def model_to_dict(model):
    """Convert SQLAlchemy model instance to dict."""
    if hasattr(model, "__table__"):
        return {c.name: getattr(model, c.name) for c in model.__table__.columns}
    return model


def camelize(obj):
    """Recursively transform keys to camelCase."""
    if isinstance(obj, dict):
        return {to_camel(k): camelize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [camelize(i) for i in obj]
    if is_dataclass(obj):
        return camelize(asdict(obj))
    # Handle SQLAlchemy models (check for __table__ attribute)
    if hasattr(obj, "__table__"):
        return camelize(model_to_dict(obj))
    return obj


class CamelCaseJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        # Automatically transform everything before it's turned into a JSON string
        return super().dumps(camelize(obj), **kwargs)

    def default(self, obj):
        # Handle types that JSON doesn't naturally understand
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        # Handle SQLAlchemy models
        if hasattr(obj, "__table__"):
            return camelize(model_to_dict(obj))
        return super().default(obj)
