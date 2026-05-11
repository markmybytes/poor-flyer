from flask.json.provider import DefaultJSONProvider

from src.database import Base


class SQLAlchemyJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if not isinstance(obj, Base):
            return super().default(obj)

        if hasattr(obj, "to_dict"):
            attr = getattr(obj, "to_dict")
            return attr() if callable(attr) else attr

        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
