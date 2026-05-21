"""Database extension module with SQLAlchemy models and initialization."""

import os
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

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

# Database path and URL configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATABASE_PATH = Path(os.getenv('DATABASE_PATH', str(BASE_DIR / 'data' / 'db.sqlite')))
DEFAULT_DATABASE_URL = f'sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}'


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Initialize SQLAlchemy extension
db = SQLAlchemy(model_class=Base, session_options={'autoflush': False})


# Database models
class Itinerary(db.Model):
    """Itinerary tracking model. Represents a multi-leg tracked trip."""

    __tablename__ = 'itineraries'

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # 'SINGLE', 'ROUND_TRIP', 'MULTI_CITY'
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    flights: Mapped[list['Flight']] = relationship(
        'Flight',
        cascade='all, delete-orphan',
        back_populates='itinerary',
        order_by='Flight.sequence',
    )


class Flight(db.Model):
    """Flight leg model."""

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
    """Fare snapshot model."""

    __tablename__ = 'fare_snapshots'

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    flight_id: Mapped[str] = mapped_column(
        String, ForeignKey('flights.id', ondelete='CASCADE'), nullable=False
    )

    flight_number: Mapped[str | None] = mapped_column(String, nullable=True)
    departure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fare: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String, nullable=True)
    scrape_status: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    flight: Mapped['Flight'] = relationship('Flight', back_populates='fare_snapshots')


class Config(db.Model):
    """Configuration model for storing app settings."""

    __tablename__ = 'config'

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (UniqueConstraint('namespace', 'key', name='uq_config_namespace_key'),)
