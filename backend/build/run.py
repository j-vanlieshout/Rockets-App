# build/run.py
# Build orchestrator: scrape -> export JSON -> detect notable results ->
# send spoiler-free pings -> persist dedup state. Run from backend/:
#
#   python -m build.run
#
# In production the GitHub Action runs this on a cron and commits docs/data/
# back to the repo (that commit doubles as the dedup memory).
#
# Heavy/network imports (scraper) are loaded lazily inside main() so that the
# pure orchestration core remains importable without them (and testable).

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from build import export, alerts

# repo_root/docs/data  (this file is backend/build/run.py)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(REPO_ROOT, "docs", "data")
STATE_FILENAME = "alert_state.json"


def load_state(path) -> list:
    """Read the list of already-alerted race keys; [] if the file is absent."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(path, keys) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2)


def process_alerts(results_by_slug, state_path, send_fn=alerts.send_ping):
    """Detect newly-notable races, ping each exactly once, persist state.

    Pure except for `send_fn` (defaults to the ntfy edge) and the state file.
    Returns the list of new pings sent this run.
    """
    qualifying = alerts.find_qualifying(results_by_slug)
    alerted = load_state(state_path)
    new, next_state = alerts.detect_new_pings(qualifying, alerted)
    for ping in new:
        send_fn(ping["race_name"])
    save_state(state_path, next_state)
    return new


def main(season=None):
    """Full build: scrape PCS, export JSON, send pings. Thin I/O shell."""
    # Lazy imports — these reach the network / need scraper deps.
    from config import CURRENT_SEASON, TRACKED_TEAMS, DATABASE_URL
    from db.sync import sync_all
    from db.models import Base
    from scraper.uci_ranking import scrape_team_ranking
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    season = season or CURRENT_SEASON

    # 1. Scrape PCS into the scratch SQLite DB.
    sync_all(season)

    # 2. Scrape the live UCI team ranking (best-effort).
    try:
        ranking_entries = scrape_team_ranking(season)
    except Exception as exc:  # noqa: BLE001 — ranking is non-critical
        print(f"WARN: ranking scrape failed: {exc}", file=sys.stderr)
        ranking_entries = []

    # 3. Export JSON for every tracked team (single-team today; loop-ready).
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        tracked_slugs = {t["slug"] for t in TRACKED_TEAMS}
        primary_slug = TRACKED_TEAMS[0]["slug"]
        export.export_all(db, DATA_DIR, season=season,
                          ranking_entries=ranking_entries,
                          team_slug=primary_slug, tracked_slugs=tracked_slugs)
        results_by_slug = export.build_results(db, season)
    finally:
        db.close()

    # 4. Detect notable results and ping (spoiler-free), deduped per race.
    state_path = os.path.join(DATA_DIR, STATE_FILENAME)
    new = process_alerts(results_by_slug, state_path)
    print(f"Build complete: {len(new)} new ping(s).")


if __name__ == "__main__":
    main()
