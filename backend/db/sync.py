# db/sync.py
# Orchestrates scraping and persists everything to SQLite.
#
# Usage (run from backend/):
#   python db/sync.py              # sync current season
#   python db/sync.py --season 2025

import logging
import argparse
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import TRACKED_TEAMS, CURRENT_SEASON, DATABASE_URL
from db.models import Base, Team, Rider, Race, RaceResult
from procyclingstats import Team as PCSTeam, Rider as PCSRider

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ── DB setup ───────────────────────────────────────────────────────────────────

def get_session() -> Session:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


# ── Name / class helpers ───────────────────────────────────────────────────────

_CLASS_RE = re.compile(r"\(([^)]+)\)\s*$")


def extract_class_from_name(name: str, fallback: str = "") -> tuple[str, str]:
    """
    PCS often embeds the race class in the stage name,
    e.g. "Clasica de Almeria (1.Pro)" → ("Clasica de Almeria", "1.Pro").
    Returns (clean_name, race_class).
    """
    m = _CLASS_RE.search(name)
    if m:
        return name[: m.start()].strip(), m.group(1)
    return name, fallback


def clean_stage_name(raw: str) -> str:
    """
    Strip PCS stage prefixes such as "S3Stage 3 - Bessèges › Bessèges"
    down to the meaningful part after the dash.
    """
    if " - " in raw:
        raw = raw.split(" - ", 1)[1]
    if raw.startswith("S") and "Stage" in raw:
        raw = raw.split("Stage", 1)[-1].split(" - ", 1)[-1]
    return raw.strip()


# ── Upsert helpers ─────────────────────────────────────────────────────────────

def upsert_team(db: Session, slug: str, name: str, uci_code: str) -> Team:
    team = db.query(Team).filter_by(slug=slug).first()
    if not team:
        team = Team(slug=slug, name=name, uci_code=uci_code)
        db.add(team)
        db.flush()
        logger.info(f"  Created team: {name}")
    else:
        team.name = name
    return team


def upsert_rider(db: Session, team: Team, roster_entry: dict, profile: dict) -> Rider:
    slug = roster_entry["rider_url"].split("/")[-1]
    rider = db.query(Rider).filter_by(pcs_slug=slug).first()
    if not rider:
        rider = Rider(pcs_slug=slug)
        db.add(rider)

    sp = profile.get("points_per_speciality", {})
    rider.full_name        = profile.get("name") or roster_entry["rider_name"]
    rider.nationality      = roster_entry.get("nationality")
    rider.age              = roster_entry.get("age")
    rider.date_of_birth    = profile.get("birthdate")
    rider.weight_kg        = profile.get("weight")
    rider.height_m         = profile.get("height")
    rider.sp_one_day_races = sp.get("one_day_races", 0)
    rider.sp_gc            = sp.get("gc", 0)
    rider.sp_time_trial    = sp.get("time_trial", 0)
    rider.sp_sprint        = sp.get("sprint", 0)
    rider.sp_climber       = sp.get("climber", 0)
    rider.sp_hills         = sp.get("hills", 0)
    rider.team_id          = team.id
    db.flush()
    return rider


def upsert_race(db: Session, stage_url: str, stage_name: str, race_class: str, season: int) -> Race:
    # Stable race slug: "race/tour-de-france/2026/stage-1" → "race/tour-de-france/2026"
    parts = stage_url.split("/")
    race_slug = "/".join(parts[:3]) if len(parts) >= 3 else stage_url

    name = clean_stage_name(stage_name)
    name, resolved_class = extract_class_from_name(name, fallback=race_class)

    race = db.query(Race).filter_by(pcs_slug=race_slug).first()
    if not race:
        race = Race(
            pcs_slug   = race_slug,
            name       = name or stage_name,
            season     = season,
            race_class = resolved_class,
        )
        db.add(race)
        db.flush()
    else:
        # Backfill class if it was missing on a previous sync
        if not race.race_class and resolved_class:
            race.race_class = resolved_class
    return race


def upsert_result(db: Session, race: Race, rider: Rider, team: Team, result_data: dict) -> None:
    stage_url = result_data.get("stage_url", "")
    existing = (
        db.query(RaceResult)
        .filter_by(race_id=race.id, rider_id=rider.id, stage=stage_url)
        .first()
    )
    values = dict(
        pcs_points = float(result_data.get("pcs_points") or 0),
        uci_points = float(result_data.get("uci_points") or 0),
        position   = result_data.get("result"),
    )
    if existing:
        for k, v in values.items():
            setattr(existing, k, v)
    else:
        db.add(RaceResult(
            race_id  = race.id,
            rider_id = rider.id,
            team_id  = team.id,
            stage    = stage_url,
            date     = result_data.get("date"),
            **values,
        ))


# ── Main sync ──────────────────────────────────────────────────────────────────

def fetch_rider_profile(rider_slug: str, season: int) -> dict:
    """
    Fetch a rider's full profile from PCS.
    Tries the season-specific URL first, falls back to the generic URL.
    Returns an empty dict if the PCS library throws an unrecoverable error.
    """
    for url in [f"rider/{rider_slug}/{season}", f"rider/{rider_slug}"]:
        try:
            return PCSRider(url).parse()
        except IndexError:
            # Known PCS library bug for riders with incomplete profiles
            logger.warning(f"    [{rider_slug}] PCS library parse error — storing roster data only")
            return {}
        except Exception as exc:
            logger.warning(f"    [{rider_slug}] Failed with {url!r}: {exc} — retrying")
    return {}


def sync_team(db: Session, team_cfg: dict, season: int) -> None:
    slug = team_cfg["slug"]
    logger.info(f"\n{'='*60}")
    logger.info(f"Syncing: {team_cfg['name']} ({season})")
    logger.info(f"{'='*60}")

    team_data = PCSTeam(f"team/{slug}-{season}").parse()
    team = upsert_team(db, slug, team_data["name"], team_cfg["uci_code"])

    riders_done = results_done = 0

    for roster_entry in team_data["riders"]:
        rider_slug = roster_entry["rider_url"].split("/")[-1]
        logger.info(f"  Rider: {roster_entry['rider_name']}")

        profile = fetch_rider_profile(rider_slug, season)
        rider   = upsert_rider(db, team, roster_entry, profile)
        riders_done += 1

        for r in profile.get("season_results", []):
            if not r.get("stage_url"):
                continue
            race = upsert_race(db, r["stage_url"], r.get("stage_name", ""), r.get("class", ""), season)
            upsert_result(db, race, rider, team, r)
            results_done += 1

        db.commit()

    logger.info(f"\n✅ {team_cfg['name']}: {riders_done} riders, {results_done} results saved.")


def sync_all(season: int = CURRENT_SEASON) -> None:
    db = get_session()
    try:
        for team_cfg in TRACKED_TEAMS:
            sync_team(db, team_cfg, season)
    finally:
        db.close()
    logger.info("\n🎉 Sync complete.")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync PCS data to local SQLite database")
    parser.add_argument("--season", type=int, default=CURRENT_SEASON)
    args = parser.parse_args()
    sync_all(args.season)