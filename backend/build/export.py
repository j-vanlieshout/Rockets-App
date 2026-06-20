# build/export.py
# Build-time JSON export: turns a populated SQLAlchemy session into the
# static JSON files the frontend reads from ./data/. No web server involved.
#
# Shapes mirror the (now-retired) FastAPI endpoints so the frontend's data
# contract is unchanged:
#   standings.json  <- /teams/{slug}/uci-standings
#   ranking.json    <- /ranking/teams
#   results.json    <- /riders/{slug}/results, keyed by rider slug
#   meta.json       <- { "generated_at": <ISO timestamp> }

import json
import os
import datetime
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Team, Rider, Race, RaceResult


def build_standings(session: Session, team_slug: str, season: int) -> dict:
    """UCI points leaderboard for one team, highest first.
    Riders who haven't raced are appended at the bottom with zeros."""
    team = session.query(Team).filter(Team.slug == team_slug).first()
    if not team:
        raise ValueError(f"Team not found: {team_slug}")

    rows = (
        session.query(
            Rider,
            func.sum(RaceResult.uci_points).label("total_uci"),
            func.sum(RaceResult.pcs_points).label("total_pcs"),
            func.count(RaceResult.id).label("count"),
        )
        .join(RaceResult, RaceResult.rider_id == Rider.id)
        .join(Race, Race.id == RaceResult.race_id)
        .filter(RaceResult.team_id == team.id, Race.season == season)
        .group_by(Rider.id)
        .all()
    )

    riders = [
        {
            "rider_id": rider.id,
            "pcs_slug": rider.pcs_slug,
            "full_name": rider.full_name,
            "nationality": rider.nationality,
            "age": rider.age,
            "total_uci_points": float(total_uci or 0),
            "total_pcs_points": float(total_pcs or 0),
            "results_count": count,
        }
        for rider, total_uci, total_pcs, count in rows
    ]
    riders.sort(key=lambda e: e["total_uci_points"], reverse=True)

    raced_ids = {e["rider_id"] for e in riders}
    for rider in team.riders:
        if rider.id not in raced_ids:
            riders.append({
                "rider_id": rider.id,
                "pcs_slug": rider.pcs_slug,
                "full_name": rider.full_name,
                "nationality": rider.nationality,
                "age": rider.age,
                "total_uci_points": 0,
                "total_pcs_points": 0,
                "results_count": 0,
            })

    return {
        "team_name": team.name,
        "season": season,
        "total_uci_points": sum(e["total_uci_points"] for e in riders),
        "riders": riders,
    }


def build_results(session: Session, season: int) -> dict:
    """All rider results for a season, keyed by rider slug, most recent first.
    Riders with no results are simply absent from the mapping."""
    results = defaultdict(list)

    rows = (
        session.query(RaceResult, Race, Rider)
        .join(Race, Race.id == RaceResult.race_id)
        .join(Rider, Rider.id == RaceResult.rider_id)
        .filter(Race.season == season)
        .order_by(RaceResult.date.desc())
        .all()
    )

    for rr, race, rider in rows:
        results[rider.pcs_slug].append({
            "id": rr.id,
            "stage": rr.stage,
            "date": rr.date,
            "position": rr.position,
            "pcs_points": float(rr.pcs_points),
            "uci_points": float(rr.uci_points),
            "rider_id": rr.rider_id,
            "race_id": rr.race_id,
            "team_id": rr.team_id,
            "race_name": race.name,
            "race_class": race.race_class,
        })

    return dict(results)


def build_ranking(ranking_entries, tracked_slugs) -> list:
    """Shape scraped UCI team-ranking entries into the frontend's ranking rows,
    flagging tracked teams. Pure: takes already-scraped entries, no I/O."""
    tracked = set(tracked_slugs)
    return [
        {
            "team_name": e.team_name,
            "team_slug": e.team_slug,
            "team_class": e.team_class or "",
            "current_rank": e.uci_ranking_position,
            "prev_rank": e.prev_rank,
            "current_points": e.uci_points,
            "is_tracked": e.team_slug in tracked,
        }
        for e in ranking_entries
    ]


def export_all(session, out_dir, season, ranking_entries, team_slug, tracked_slugs,
               generated_at=None) -> None:
    """Write standings/ranking/results/meta JSON into out_dir.
    `generated_at` defaults to now (UTC, ISO 8601) and feeds the UI's
    'Last updated' label."""
    os.makedirs(out_dir, exist_ok=True)
    if generated_at is None:
        generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    payloads = {
        "standings.json": build_standings(session, team_slug, season),
        "ranking.json": build_ranking(ranking_entries or [], tracked_slugs),
        "results.json": build_results(session, season),
        "meta.json": {"generated_at": generated_at, "season": season},
    }
    for name, data in payloads.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
