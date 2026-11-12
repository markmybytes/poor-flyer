import collections.abc
import logging
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime

from flask.json.provider import DefaultJSONProvider
from sqlalchemy import inspect

from src.extensions.database import floating_datetime

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


def to_camel(snake_str):
    """Converts snake_case to camelCase."""
    parts = snake_str.split('_')
    return parts[0] + ''.join(x.title() for x in parts[1:])


def model_to_dict(model):
    """Convert SQLAlchemy model instance to dict, including loaded relationships."""
    if not hasattr(model, '__table__'):
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

    # Handle dicts AND SQLAlchemy RowMappings (anything that acts like a dict)
    if isinstance(obj, collections.abc.Mapping):
        return {to_camel(k): camelize(v) for k, v in obj.items()}

    # Handle SQLAlchemy Raw Rows (converts them to dicts first)
    if hasattr(obj, '_mapping'):
        return camelize(dict(obj._mapping))

    # Handle standard iterables (lists, tuples)
    if isinstance(obj, (list, tuple)):
        return [camelize(i) for i in obj]

    # Handle Dataclasses
    if is_dataclass(obj):
        return camelize(asdict(obj))

    # Handle full SQLAlchemy Models
    if hasattr(obj, '__table__'):
        return camelize(model_to_dict(obj))
    return obj


class CamelCaseJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        if isinstance(obj, (dict, list)):
            obj = camelize(obj)
        return super().dumps(obj, **kwargs)

    def default(self, obj):
        if isinstance(obj, floating_datetime):
            return obj.isoformat()

        if isinstance(obj, datetime):
            if obj.tzinfo is None:
                # naive datetimes are flight-local wall-clock times everywhere in
                # this schema (UTCDateTime covers the UTC ones) — serialize them
                # without a zone suffix instead of pretending they are UTC
                logger.debug('serialize naive datetime as flight-local')
                return obj.isoformat()
            normalized = obj.astimezone(UTC)
            return normalized.isoformat().replace('+00:00', 'Z')

        if isinstance(obj, date):
            return obj.isoformat()

        if hasattr(obj, '__table__'):
            return camelize(model_to_dict(obj))

        return super().default(obj)
