import logging
import uuid
from datetime import UTC, date, datetime

import sqlalchemy.types as types
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base, session_options={'autoflush': False})


class floating_datetime(datetime):
    """A marker subclass indicating this datetime is INTENTIONALLY timezone-unaware."""

    pass


class UTCDateTime(types.TypeDecorator):  # Timezone-Aware Force Type for SQLite
    """
    Custom DateTime decorator that forces SQLite to return timezone-aware
    UTC datetime objects instead of naive datetimes, silencing the false-positive
    JSON serialization warning spam.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            return value.astimezone(UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class FloatingDateTime(types.TypeDecorator):
    """
    Maps to standard DateTime(timezone=False).
    Returns a 'floating_datetime' instance so the serializer knows not to alarm logs.
    """

    impl = DateTime(timezone=False)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None:
            # Reconstruct as our explicit marker subclass
            return floating_datetime(
                value.year,
                value.month,
                value.day,
                value.hour,
                value.minute,
                value.second,
                value.microsecond,
            )
        return value


class Itinerary(db.Model):
    __tablename__ = 'itineraries'

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_type: Mapped[str] = mapped_column(String, nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(UTC))

    flights: Mapped[list['Flight']] = relationship(
        'Flight',
        cascade='all, delete-orphan',
        back_populates='itinerary',
        order_by='Flight.sequence',
    )


class Flight(db.Model):
    __tablename__ = 'flights'

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    itinerary_id: Mapped[str] = mapped_column(
        String, ForeignKey('itineraries.id', ondelete='CASCADE'), nullable=False
    )
    sequence: Mapped[int] = mapped_column(db.Integer, nullable=False)
    origin: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    flight_date: Mapped[date] = mapped_column(Date, nullable=False)

    itinerary: Mapped['Itinerary'] = relationship('Itinerary', back_populates='flights')
    fare_snapshots: Mapped[list['FareSnapshot']] = relationship(
        'FareSnapshot', cascade='all, delete-orphan', back_populates='flight'
    )


class FareSnapshot(db.Model):
    __tablename__ = 'fare_snapshots'

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    flight_id: Mapped[str] = mapped_column(
        String, ForeignKey('flights.id', ondelete='CASCADE'), nullable=False
    )

    flight_number: Mapped[str | None] = mapped_column(String, nullable=True)

    departure_at: Mapped[datetime | None] = mapped_column(FloatingDateTime, nullable=True)
    arrival_at: Mapped[datetime | None] = mapped_column(FloatingDateTime, nullable=True)

    fare: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String, nullable=True)
    scrape_status: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(UTC))

    flight: Mapped['Flight'] = relationship('Flight', back_populates='fare_snapshots')


class Config(db.Model):
    __tablename__ = 'config'

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (UniqueConstraint('namespace', 'key', name='uq_config_namespace_key'),)
