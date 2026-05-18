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
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
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
class Flight(db.Model):
    """Flight tracking model."""

    __tablename__ = 'flights'

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    origin: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    flight_date: Mapped[date] = mapped_column(Date, nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    fare_snapshots: Mapped[list['FlightFareSnapshot']] = relationship(
        'FlightFareSnapshot', cascade='all, delete-orphan', back_populates='flight'
    )


class FlightFareSnapshot(db.Model):
    """Flight fare snapshot model."""

    __tablename__ = 'flight_fare_snapshots'

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    flight_id: Mapped[str] = mapped_column(
        String, ForeignKey('flights.id', ondelete='CASCADE'), nullable=False
    )

    fare: Mapped[float | None] = mapped_column(Float, nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String, nullable=True)
    departure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scrape_status: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
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


# Session and engine initialization for direct database access (e.g., scripts)
engine = create_engine(
    DEFAULT_DATABASE_URL,
    connect_args={'check_same_thread': False} if DEFAULT_DATABASE_URL.startswith('sqlite') else {},
)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db() -> None:
    """Initialize database schema for direct/script usage.

    Flask extension binding is handled in src.extensions.init_extensions.
    """
    DEFAULT_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_session():
    """Get current database session.

    Returns:
        SQLAlchemy session object
    """
    return db.session
