# scraper/uci_ranking.py
# Fetches the live UCI team ranking from ProCyclingStats.
#
# Run directly to print the current ranking:
#   python scraper/uci_ranking.py

import logging
import argparse
from dataclasses import dataclass
from typing import Optional

from procyclingstats import Ranking

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import TRACKED_TEAMS, CURRENT_SEASON

logger = logging.getLogger(__name__)


@dataclass
class TeamRankingEntry:
    season:               int
    team_name:            str
    team_slug:            str
    team_class:           str           # "WT", "PRT", or "CT"
    uci_ranking_position: Optional[int]
    prev_rank:            Optional[int]
    uci_points:           float


def scrape_team_ranking(season: int = CURRENT_SEASON) -> list[TeamRankingEntry]:
    """
    Fetch the current UCI team ranking from PCS.
    Returns all teams sorted by rank. Raises on network/parse failure
    so callers can decide how to handle errors.
    """
    data = Ranking("rankings/me/teams").parse()
    rows = data.get("team_ranking") or []

    entries = []
    for row in rows:
        team_url       = row.get("team_url", "")
        team_slug_full = team_url.split("/")[-1] if team_url else ""
        # Strip year suffix: "unibet-rose-rockets-2026" → "unibet-rose-rockets"
        team_slug = "-".join(team_slug_full.split("-")[:-1]) if team_slug_full else team_slug_full

        entries.append(TeamRankingEntry(
            season               = season,
            team_name            = row.get("team_name", "").strip(),
            team_slug            = team_slug,
            team_class           = row.get("class", ""),
            uci_ranking_position = row.get("rank"),
            prev_rank            = row.get("prev_rank"),
            uci_points           = float(row.get("points") or 0),
        ))

    return entries


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Print the current UCI team ranking")
    parser.add_argument("--season", type=int, default=CURRENT_SEASON)
    parser.add_argument("--all",    action="store_true", help="Show all teams, not just WT/PRT")
    args = parser.parse_args()

    tracked_slugs = {t["slug"] for t in TRACKED_TEAMS}

    try:
        entries = scrape_team_ranking(args.season)
    except Exception as e:
        print(f"Error fetching ranking: {e}")
        raise SystemExit(1)

    visible = entries if args.all else [e for e in entries if e.team_class in ("WT", "PRT")]
    print(f"\nUCI Team Ranking — {args.season}  ({len(entries)} total teams)\n{'='*60}")
    for e in visible:
        trend  = f"▲{e.prev_rank - e.uci_ranking_position}" if e.prev_rank and e.uci_ranking_position and e.prev_rank > e.uci_ranking_position \
                 else f"▼{e.uci_ranking_position - e.prev_rank}" if e.prev_rank and e.uci_ranking_position and e.prev_rank < e.uci_ranking_position \
                 else "="
        marker = " ◄" if e.team_slug in tracked_slugs else ""
        print(f"  #{e.uci_ranking_position or '?':>3} {trend:>4}  [{e.team_class:<3}]  {e.team_name:<38} {e.uci_points:>6.0f} pts{marker}")