# db/models.py
# SQLAlchemy ORM models — stored in a local SQLite file.
# Run `python -m db.models` to create all tables.

from sqlalchemy import (
    Column, Integer, String, Float,
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
    slug     = Column(String, nullable=False, unique=True)
    uci_code = Column(String(10))

    riders  = relationship("Rider", back_populates="team")
    results = relationship("RaceResult", back_populates="team")


class Rider(Base):
    __tablename__ = "riders"

    id               = Column(Integer, primary_key=True)
    pcs_slug         = Column(String, nullable=False, unique=True)
    full_name        = Column(String, nullable=False)
    nationality      = Column(String(3))
    date_of_birth    = Column(String)    # "YYYY-M-D" string as returned by PCS
    age              = Column(Integer)
    weight_kg        = Column(Float)
    height_m         = Column(Float)
    # Career speciality points from PCS
    sp_one_day_races = Column(Integer, default=0)
    sp_gc            = Column(Integer, default=0)
    sp_time_trial    = Column(Integer, default=0)
    sp_sprint        = Column(Integer, default=0)
    sp_climber       = Column(Integer, default=0)
    sp_hills         = Column(Integer, default=0)

    team_id = Column(Integer, ForeignKey("teams.id"))
    team    = relationship("Team", back_populates="riders")
    results = relationship("RaceResult", back_populates="rider")


class Race(Base):
    __tablename__ = "races"

    id         = Column(Integer, primary_key=True)
    pcs_slug   = Column(String, nullable=False, unique=True)
    name       = Column(String, nullable=False)
    season     = Column(Integer)
    race_class = Column(String)    # e.g. "2.UWT", "1.Pro"

    results = relationship("RaceResult", back_populates="race")


class RaceResult(Base):
    __tablename__ = "race_results"
    __table_args__ = (
        UniqueConstraint("race_id", "rider_id", "stage", name="uq_result"),
    )

    id         = Column(Integer, primary_key=True)
    race_id    = Column(Integer, ForeignKey("races.id"), nullable=False)
    rider_id   = Column(Integer, ForeignKey("riders.id"), nullable=False)
    team_id    = Column(Integer, ForeignKey("teams.id"), nullable=False)
    stage      = Column(String)        # stage URL slug, used as unique identifier
    date       = Column(String)        # "YYYY-MM-DD"
    position   = Column(Integer)       # finishing position (1 = win)
    pcs_points = Column(Float, default=0)
    uci_points = Column(Float, default=0)

    race  = relationship("Race", back_populates="results")
    rider = relationship("Rider", back_populates="results")
    team  = relationship("Team", back_populates="results")


# ── Create tables ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = create_engine(DATABASE_URL, echo=True)
    Base.metadata.create_all(engine)
    print("✅ All tables created.")