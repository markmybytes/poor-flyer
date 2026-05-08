import os
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/db.sqlite")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TrackingEntry(Base):
    __tablename__ = "tracking_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    flight_date = Column(Date, nullable=False)
    adult_count = Column(Integer, default=1)
    child_count = Column(Integer, default=0)
    infant_count = Column(Integer, default=0)
    deadline = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    price_snapshots = relationship(
        "PriceSnapshot", cascade="all, delete-orphan", back_populates="tracking_entry"
    )


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    entry_id = Column(
        String, ForeignKey("tracking_entries.id", ondelete="CASCADE"), nullable=False
    )
    scraped_at = Column(DateTime, nullable=False)
    fare = Column(Numeric(10, 2), nullable=True)
    flight_number = Column(String, nullable=True)
    departure_time = Column(String, nullable=True)
    arrival_time = Column(String, nullable=True)
    scrape_status = Column(String, nullable=False)
    error_message = Column(String, nullable=True)

    tracking_entry = relationship("TrackingEntry", back_populates="price_snapshots")


def init_db():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
