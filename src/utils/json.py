from dataclasses import asdict, is_dataclass
from datetime import date, datetime

from flask.json.provider import DefaultJSONProvider
from sqlalchemy import inspect


def to_camel(snake_str):
    """Converts snake_case to camelCase."""
    parts = snake_str.split("_")
    return parts[0] + "".join(x.title() for x in parts[1:])


def model_to_dict(model):
    """Convert SQLAlchemy model instance to dict, including loaded relationships."""
    if not hasattr(model, "__table__"):
        return model

    # Grab all standard columns
    result = {c.name: getattr(model, c.name) for c in model.__table__.columns}

    # Grab eagerly loaded relationships
    inspected = inspect(model)
    for relation in inspected.mapper.relationships:
        # Only include the relationship if it has already been loaded
        if relation.key not in inspected.unloaded:
            result[relation.key] = getattr(model, relation.key)

    return result


def camelize(obj):
    """Recursively transform keys to camelCase."""
    if isinstance(obj, dict):
        return {to_camel(k): camelize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [camelize(i) for i in obj]
    if is_dataclass(obj):
        return camelize(asdict(obj))
    # Handle SQLAlchemy models
    if hasattr(obj, "__table__"):
        return camelize(model_to_dict(obj))
    return obj


class CamelCaseJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        return super().dumps(camelize(obj), **kwargs)

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, "__table__"):
            return camelize(model_to_dict(obj))
        return super().default(obj)
