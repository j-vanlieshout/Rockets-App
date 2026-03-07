# db/models.py
# SQLAlchemy ORM models — stored in a local SQLite file.
# Run `python -m db.models` to create all tables.

from sqlalchemy import (
    Column, Integer, String, Date, Float,
    ForeignKey, UniqueConstraint, create_engine
)
from sqlalchemy.orm import declarative_base, relationship

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL

Base = declarative_base()


class Team(Base):
    __tablename__ = "teams"

    id       = Column(Integer, primary_key=True)
    name     = Column(String, nullable=False)
    slug     = Column(String, nullable=False, unique=True)   # PCS slug prefix
    uci_code = Column(String(10))

    riders  = relationship("Rider", back_populates="team")
    results = relationship("RaceResult", back_populates="team")


class Rider(Base):
    __tablename__ = "riders"

    id              = Column(Integer, primary_key=True)
    pcs_slug        = Column(String, nullable=False, unique=True)
    full_name       = Column(String, nullable=False)
    nationality     = Column(String(3))
    date_of_birth   = Column(Date)
    age             = Column(Integer)
    weight_kg       = Column(Integer)
    height_cm       = Column(Integer)
    specialty       = Column(String)
    pcs_ranking     = Column(Integer)
    pcs_points      = Column(Integer)
    profile_url     = Column(String)

    team_id = Column(Integer, ForeignKey("teams.id"))
    team    = relationship("Team", back_populates="riders")

    results = relationship("RaceResult", back_populates="rider")


class Race(Base):
    __tablename__ = "races"

    id         = Column(Integer, primary_key=True)
    pcs_slug   = Column(String, nullable=False, unique=True)
    name       = Column(String, nullable=False)
    season     = Column(Integer)
    start_date = Column(Date)
    end_date   = Column(Date)
    category   = Column(String)    # e.g. "2.UWT", "1.Pro", "GT"
    country    = Column(String)

    results = relationship("RaceResult", back_populates="race")


class RaceResult(Base):
    __tablename__ = "race_results"
    __table_args__ = (
        UniqueConstraint("race_id", "rider_id", "stage", name="uq_result"),
    )

    id        = Column(Integer, primary_key=True)
    race_id   = Column(Integer, ForeignKey("races.id"), nullable=False)
    rider_id  = Column(Integer, ForeignKey("riders.id"), nullable=False)
    team_id   = Column(Integer, ForeignKey("teams.id"), nullable=False)
    stage     = Column(String)       # "GC", "Stage 1", "Points", etc.
    position  = Column(Integer)      # finishing position (1 = win)
    time_gap  = Column(String)       # e.g. "+0:45"
    points    = Column(Integer)      # PCS points earned

    race  = relationship("Race", back_populates="results")
    rider = relationship("Rider", back_populates="results")
    team  = relationship("Team", back_populates="results")


# ── Create tables ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = create_engine(DATABASE_URL, echo=True)
    Base.metadata.create_all(engine)
    print("✅ All tables created.")
