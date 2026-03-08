# api/main.py
# FastAPI REST layer — the Android app talks to these endpoints.
#
# Start with:
#   uvicorn api.main:app --reload
#
# Interactive docs at:
#   http://127.0.0.1:8000/docs

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, ConfigDict
from typing import Optional
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATABASE_URL, CURRENT_SEASON, TRACKED_TEAMS
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

# ── Pydantic response schemas ──────────────────────────────────────────────────
# These define exactly what JSON shape the Android app receives.

class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:       int
    name:     str
    slug:     str
    uci_code: Optional[str]


class RiderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              int
    pcs_slug:        str
    full_name:       str
    nationality:     Optional[str]
    date_of_birth:   Optional[str]
    age:             Optional[int]
    weight_kg:       Optional[float]
    height_m:        Optional[float]
    sp_one_day_races: int
    sp_gc:           int
    sp_time_trial:   int
    sp_sprint:       int
    sp_climber:      int
    sp_hills:        int
    team_id:         Optional[int]


class RaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    pcs_slug:   str
    name:       str
    season:     Optional[int]
    race_class: Optional[str]


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         int
    stage:      Optional[str]
    date:       Optional[str]
    position:   Optional[int]
    pcs_points: float
    uci_points: float
    rider_id:   int
    race_id:    int
    team_id:    int


class RiderResultOut(ResultOut):
    """Result enriched with race info — used in rider detail view."""
    race_name:  str
    race_class: Optional[str]


class RaceResultOut(ResultOut):
    """Result enriched with rider info — used in race detail view."""
    rider_name:        str
    rider_nationality: Optional[str]


class UCIStandingEntry(BaseModel):
    """One row in the team UCI standings table."""
    rider_id:          int
    pcs_slug:          str
    full_name:         str
    nationality:       Optional[str]
    age:               Optional[int]
    total_uci_points:  float
    total_pcs_points:  float
    results_count:     int


class TeamUCIStandings(BaseModel):
    team_name:        str
    season:           int
    total_uci_points: float
    riders:           list[UCIStandingEntry]


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PCS Team Tracker API",
    description="Serves scraped ProCyclingStats data to the Android app.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Teams ──────────────────────────────────────────────────────────────────────

@app.get("/teams", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    """List all tracked teams."""
    return db.query(Team).all()


@app.get("/teams/{slug}", response_model=TeamOut)
def get_team(slug: str, db: Session = Depends(get_db)):
    """Get a single team by PCS slug."""
    team = db.query(Team).filter(Team.slug == slug).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@app.get("/teams/{slug}/riders", response_model=list[RiderOut])
def get_team_riders(slug: str, db: Session = Depends(get_db)):
    """Full rider roster for a team, sorted alphabetically."""
    team = db.query(Team).filter(Team.slug == slug).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return sorted(team.riders, key=lambda r: r.full_name)


@app.get("/teams/{slug}/uci-standings", response_model=TeamUCIStandings)
def get_team_uci_standings(
    slug: str,
    season: int = CURRENT_SEASON,
    db: Session = Depends(get_db),
):
    """
    UCI points leaderboard for a team — the most important endpoint.
    Returns every rider's UCI point total for the season, sorted highest first.
    """
    team = db.query(Team).filter(Team.slug == slug).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Aggregate UCI + PCS points per rider for this season
    rows = (
        db.query(
            Rider,
            func.sum(RaceResult.uci_points).label("total_uci"),
            func.sum(RaceResult.pcs_points).label("total_pcs"),
            func.count(RaceResult.id).label("count"),
        )
        .join(RaceResult, RaceResult.rider_id == Rider.id)
        .join(Race, Race.id == RaceResult.race_id)
        .filter(RaceResult.team_id == team.id)
        .filter(Race.season == season)
        .group_by(Rider.id)
        .all()
    )

    entries = [
        UCIStandingEntry(
            rider_id         = rider.id,
            pcs_slug         = rider.pcs_slug,
            full_name        = rider.full_name,
            nationality      = rider.nationality,
            age              = rider.age,
            total_uci_points = float(total_uci or 0),
            total_pcs_points = float(total_pcs or 0),
            results_count    = count,
        )
        for rider, total_uci, total_pcs, count in rows
    ]
    entries.sort(key=lambda e: e.total_uci_points, reverse=True)

    # Also include riders with 0 points (not yet raced)
    raced_ids = {e.rider_id for e in entries}
    for rider in team.riders:
        if rider.id not in raced_ids:
            entries.append(UCIStandingEntry(
                rider_id         = rider.id,
                pcs_slug         = rider.pcs_slug,
                full_name        = rider.full_name,
                nationality      = rider.nationality,
                age              = rider.age,
                total_uci_points = 0,
                total_pcs_points = 0,
                results_count    = 0,
            ))

    return TeamUCIStandings(
        team_name        = team.name,
        season           = season,
        total_uci_points = sum(e.total_uci_points for e in entries),
        riders           = entries,
    )


# ── Riders ─────────────────────────────────────────────────────────────────────

@app.get("/riders/{slug}", response_model=RiderOut)
def get_rider(slug: str, db: Session = Depends(get_db)):
    """Full rider profile."""
    rider = db.query(Rider).filter(Rider.pcs_slug == slug).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    return rider


@app.get("/riders/{slug}/results", response_model=list[RiderResultOut])
def get_rider_results(
    slug: str,
    season: int = CURRENT_SEASON,
    db: Session = Depends(get_db),
):
    """All race results for a rider in a given season, most recent first."""
    rider = db.query(Rider).filter(Rider.pcs_slug == slug).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    rows = (
        db.query(RaceResult, Race)
        .join(Race, Race.id == RaceResult.race_id)
        .filter(RaceResult.rider_id == rider.id)
        .filter(Race.season == season)
        .order_by(RaceResult.date.desc())
        .all()
    )

    return [
        RiderResultOut(
            id         = rr.id,
            stage      = rr.stage,
            date       = rr.date,
            position   = rr.position,
            pcs_points = rr.pcs_points,
            uci_points = rr.uci_points,
            rider_id   = rr.rider_id,
            race_id    = rr.race_id,
            team_id    = rr.team_id,
            race_name  = race.name,
            race_class = race.race_class,
        )
        for rr, race in rows
    ]


# ── Races ──────────────────────────────────────────────────────────────────────

@app.get("/races", response_model=list[RaceOut])
def list_races(season: int = CURRENT_SEASON, db: Session = Depends(get_db)):
    """All races with results in a given season."""
    return db.query(Race).filter(Race.season == season).order_by(Race.pcs_slug).all()


@app.get("/races/{race_id}/results", response_model=list[RaceResultOut])
def get_race_results(race_id: int, db: Session = Depends(get_db)):
    """All tracked rider results for a specific race, sorted by position."""
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    rows = (
        db.query(RaceResult, Rider)
        .join(Rider, Rider.id == RaceResult.rider_id)
        .filter(RaceResult.race_id == race_id)
        .order_by(RaceResult.uci_points.desc())
        .all()
    )

    return [
        RaceResultOut(
            id                = rr.id,
            stage             = rr.stage,
            date              = rr.date,
            position          = rr.position,
            pcs_points        = rr.pcs_points,
            uci_points        = rr.uci_points,
            rider_id          = rr.rider_id,
            race_id           = rr.race_id,
            team_id           = rr.team_id,
            rider_name        = rider.full_name,
            rider_nationality = rider.nationality,
        )
        for rr, rider in rows
    ]

# ── Team Ranking ───────────────────────────────────────────────────────────────

class TeamRankingOut(BaseModel):
    team_name:      str
    team_slug:      str
    team_class:     str
    current_rank:   Optional[int]
    prev_rank:      Optional[int]
    current_points: float
    is_tracked:     bool


@app.get("/ranking/teams", response_model=list[TeamRankingOut])
def get_team_ranking(
    season: int = CURRENT_SEASON,
    db: Session = Depends(get_db),
):
    """UCI team ranking scraped live from PCS."""
    from scraper.uci_ranking import scrape_team_ranking

    tracked_slugs = {t["slug"] for t in TRACKED_TEAMS}
    entries = scrape_team_ranking(season)

    return [
        TeamRankingOut(
            team_name      = e.team_name,
            team_slug      = e.team_slug,
            team_class     = e.team_class or "",
            current_rank   = e.uci_ranking_position,
            prev_rank      = e.prev_rank,
            current_points = e.uci_points,
            is_tracked     = e.team_slug in tracked_slugs,
        )
        for e in entries
    ]