import os
import uuid
from datetime import UTC, date, datetime

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
    mapped_column,
    relationship,
    sessionmaker,
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/db.sqlite")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Flight(Base):
    __tablename__ = "flights"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    origin: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    flight_date: Mapped[date] = mapped_column(Date, nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    fare_snapshots: Mapped[list["FlightFareSnapshot"]] = relationship(
        "FlightFareSnapshot", cascade="all, delete-orphan", back_populates="flight"
    )


class FlightFareSnapshot(Base):
    __tablename__ = "flight_fare_snapshots"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    flight_id: Mapped[str] = mapped_column(
        String, ForeignKey("flights.id", ondelete="CASCADE"), nullable=False
    )

    fare: Mapped[float | None] = mapped_column(Float, nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String, nullable=True)
    departure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scrape_status: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    flight: Mapped["Flight"] = relationship("Flight", back_populates="fare_snapshots")


class Config(Base):
    __tablename__ = "config"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    namespace: Mapped[str] = mapped_column(String, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("namespace", "key", name="uq_config_namespace_key"),
    )


def init_db():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

