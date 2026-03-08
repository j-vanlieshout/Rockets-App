# db/sync.py
# Orchestrates scraping and persists everything to SQLite.
#
# Usage:
#   python sync.py              # sync current season
#   python sync.py --season 2025

import logging
import argparse
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import TRACKED_TEAMS, CURRENT_SEASON, DATABASE_URL
from db.models import Base, Team, Rider, Race, RaceResult, TeamRankingSnapshot
from scraper.uci_ranking import scrape_team_ranking
from procyclingstats import Team as PCSTeam, Rider as PCSRider

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ── DB setup ───────────────────────────────────────────────────────────────────

def get_session() -> Session:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


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


def upsert_rider(db: Session, team: Team, rider_data: dict, profile: dict) -> Rider:
    slug = rider_data["rider_url"].split("/")[-1]
    rider = db.query(Rider).filter_by(pcs_slug=slug).first()

    sp = profile.get("points_per_speciality", {})

    if not rider:
        rider = Rider(pcs_slug=slug)
        db.add(rider)

    rider.full_name       = profile.get("name", rider_data["rider_name"])
    rider.nationality     = rider_data.get("nationality")
    rider.age             = rider_data.get("age")
    rider.date_of_birth   = profile.get("birthdate")
    rider.weight_kg       = profile.get("weight")
    rider.height_m        = profile.get("height")
    rider.sp_one_day_races = sp.get("one_day_races", 0)
    rider.sp_gc            = sp.get("gc", 0)
    rider.sp_time_trial    = sp.get("time_trial", 0)
    rider.sp_sprint        = sp.get("sprint", 0)
    rider.sp_climber       = sp.get("climber", 0)
    rider.sp_hills         = sp.get("hills", 0)
    rider.team_id          = team.id

    db.flush()
    return rider


def extract_class_from_name(stage_name: str, fallback: str = "") -> tuple[str, str]:
    """
    PCS often embeds the race class in the name, e.g. "Clasica de Almeria (1.Pro)".
    Returns (clean_name, race_class).
    """
    import re
    m = re.search(r"\(([^)]+)\)\s*$", stage_name)
    if m:
        race_class = m.group(1)
        clean_name = stage_name[:m.start()].strip()
        return clean_name, race_class
    return stage_name, fallback


def upsert_race(db: Session, stage_url: str, stage_name: str, race_class: str, season: int) -> Race:
    # Derive a stable race slug from the stage URL
    # e.g. "race/tour-de-france/2026/stage-1" -> "tour-de-france/2026"
    parts = stage_url.split("/")
    race_slug = "/".join(parts[:3]) if len(parts) >= 3 else stage_url

    # Clean up stage name and extract race class
    # Handle stage prefixes like "S3Stage 3 - Bessèges › Bessèges"
    name = stage_name
    if " - " in name:
        name = name.split(" - ", 1)[1]  # take the part after the dash
    if name.startswith("S") and "Stage" in name:
        name = name.split("Stage", 1)[-1].split(" - ", 1)[-1].strip()

    # Extract class from name if not provided, e.g. "Clasica de Almeria (1.Pro)"
    name, resolved_class = extract_class_from_name(name, fallback=race_class)

    race = db.query(Race).filter_by(pcs_slug=race_slug).first()
    if not race:
        race = Race(
            pcs_slug=race_slug,
            name=name or stage_name,
            season=season,
            race_class=resolved_class,
        )
        db.add(race)
        db.flush()
    else:
        # Update class if it was missing before
        if not race.race_class and resolved_class:
            race.race_class = resolved_class
    return race


def upsert_result(
    db: Session,
    race: Race,
    rider: Rider,
    team: Team,
    result_data: dict,
) -> None:
    stage_url = result_data.get("stage_url", "")
    existing = (
        db.query(RaceResult)
        .filter_by(race_id=race.id, rider_id=rider.id, stage=stage_url)
        .first()
    )
    if not existing:
        result = RaceResult(
            race_id    = race.id,
            rider_id   = rider.id,
            team_id    = team.id,
            stage      = stage_url,
            date       = result_data.get("date"),
            position   = result_data.get("result"),
            pcs_points = float(result_data.get("pcs_points") or 0),
            uci_points = float(result_data.get("uci_points") or 0),
        )
        db.add(result)
    else:
        existing.pcs_points = float(result_data.get("pcs_points") or 0)
        existing.uci_points = float(result_data.get("uci_points") or 0)
        existing.position   = result_data.get("result")


# ── Main sync ──────────────────────────────────────────────────────────────────

def sync_team(db: Session, team_cfg: dict, season: int):
    slug = team_cfg["slug"]
    logger.info(f"\n{'='*60}")
    logger.info(f"Syncing: {team_cfg['name']} ({season})")
    logger.info(f"{'='*60}")

    # 1. Fetch team roster from PCS
    team_data = PCSTeam(f"team/{slug}-{season}").parse()
    team = upsert_team(db, slug, team_data["name"], team_cfg["uci_code"])

    riders_done = 0
    results_done = 0

    for roster_entry in team_data["riders"]:
        rider_slug = roster_entry["rider_url"].split("/")[-1]
        logger.info(f"  Rider: {roster_entry['rider_name']}")

        # 2. Fetch full rider profile (includes season_results with uci_points)
        # Try season-specific URL first, fall back to generic, then skip if library crashes
        profile = {}
        for url in [f"rider/{rider_slug}/{season}", f"rider/{rider_slug}"]:
            try:
                profile = PCSRider(url).parse()
                break
            except IndexError:
                logger.info(f"    Skipping profile parse for {rider_slug} (library parse error)")
                break
            except Exception as e:
                logger.info(f"    Retrying {rider_slug} with fallback URL ({e})")
                continue

        rider = upsert_rider(db, team, roster_entry, profile)
        riders_done += 1

        # 3. Save each race result
        for r in profile.get("season_results", []):
            stage_url  = r.get("stage_url", "")
            stage_name = r.get("stage_name", "")
            race_class = r.get("class", "")

            if not stage_url:
                continue

            race = upsert_race(db, stage_url, stage_name, race_class, season)
            upsert_result(db, race, rider, team, r)
            results_done += 1

        db.commit()

    logger.info(f"\n✅ {team_cfg['name']}: {riders_done} riders, {results_done} results saved.")


def sync_ranking(db: Session, season: int = CURRENT_SEASON):
    """
    Fetch the current UCI team ranking and persist it as a snapshot for this season.
    Re-running updates the snapshot in place (upsert by season + team_slug).
    """
    from datetime import datetime

    logger.info(f"Fetching UCI team ranking for {season}...")
    entries = scrape_team_ranking(season)
    if not entries:
        logger.warning("No ranking data returned — skipping.")
        return

    synced_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    for e in entries:
        existing = db.query(TeamRankingSnapshot).filter_by(
            season=season, team_slug=e.team_slug
        ).first()
        if existing:
            existing.rank       = e.uci_ranking_position
            existing.prev_rank  = e.prev_rank
            existing.points     = e.uci_points
            existing.team_class = e.team_class
            existing.team_name  = e.team_name
            existing.synced_at  = synced_at
        else:
            db.add(TeamRankingSnapshot(
                season     = season,
                team_slug  = e.team_slug,
                team_name  = e.team_name,
                team_class = e.team_class,
                rank       = e.uci_ranking_position,
                prev_rank  = e.prev_rank,
                points     = e.uci_points,
                synced_at  = synced_at,
            ))
    db.commit()
    logger.info(f"✅ Ranking snapshot saved: {len(entries)} teams for {season}.")


def sync_all(season: int = CURRENT_SEASON):
    db = get_session()
    try:
        for team_cfg in TRACKED_TEAMS:
            sync_team(db, team_cfg, season)
        sync_ranking(db, season)
    finally:
        db.close()

    logger.info("\n🎉 Sync complete.")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync PCS data to local SQLite database")
    parser.add_argument("--season", type=int, default=CURRENT_SEASON)
    args = parser.parse_args()
    sync_all(args.season)