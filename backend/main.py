# api/main.py
# FastAPI REST layer — the Android app talks to these endpoints.

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL, CURRENT_SEASON
from db.models import Base, Team, Rider, Race, RaceResult

# ── DB setup ───────────────────────────────────────────────────────────────────

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PCS Team Tracker API",
    description="Serves scraped ProCyclingStats data to the Android app.",
    version="0.1.0",
)

# ── Teams ──────────────────────────────────────────────────────────────────────

@app.get("/teams")
def list_teams(db: Session = Depends(get_db)):
    """List all tracked teams."""
    return db.query(Team).all()


@app.get("/teams/{slug}")
def get_team(slug: str, db: Session = Depends(get_db)):
    """Get a single team by its PCS slug."""
    team = db.query(Team).filter(Team.slug == slug).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@app.get("/teams/{slug}/riders")
def get_team_riders(slug: str, db: Session = Depends(get_db)):
    """Get the full rider roster for a team."""
    team = db.query(Team).filter(Team.slug == slug).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team.riders


@app.get("/teams/{slug}/results")
def get_team_results(
    slug: str,
    season: Optional[int] = CURRENT_SEASON,
    db: Session = Depends(get_db),
):
    """Get race results for a team, optionally filtered by season."""
    team = db.query(Team).filter(Team.slug == slug).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    query = db.query(RaceResult).filter(RaceResult.team_id == team.id)
    if season:
        query = query.join(Race).filter(Race.season == season)
    return query.order_by(RaceResult.id.desc()).all()


# ── Riders ─────────────────────────────────────────────────────────────────────

@app.get("/riders/{slug}")
def get_rider(slug: str, db: Session = Depends(get_db)):
    """Get a full rider profile by PCS slug."""
    rider = db.query(Rider).filter(Rider.pcs_slug == slug).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    return rider


# ── Races ──────────────────────────────────────────────────────────────────────

@app.get("/races")
def list_races(season: Optional[int] = CURRENT_SEASON, db: Session = Depends(get_db)):
    """List all races for a given season."""
    return db.query(Race).filter(Race.season == season).all()


@app.get("/races/{slug}/results")
def get_race_results(slug: str, db: Session = Depends(get_db)):
    """Get all tracked results for a specific race."""
    race = db.query(Race).filter(Race.pcs_slug == slug).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    return race.results
