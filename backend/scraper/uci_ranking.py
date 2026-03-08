# scraper/uci_ranking.py
# Scrapes the UCI Team Ranking from PCS for tracked teams.
# The 3-year rolling ranking determines WorldTour license eligibility.
#
# Run directly:
#   python uci_ranking.py
#   python uci_ranking.py --season 2025

import logging
import argparse
from dataclasses import dataclass
from typing import Optional

from procyclingstats import Ranking

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import TRACKED_TEAMS, CURRENT_SEASON

logger = logging.getLogger(__name__)


@dataclass
class TeamRankingEntry:
    season: int
    team_name: str
    team_slug: str
    team_class: str               # "WT", "PRT", "CT"
    uci_ranking_position: Optional[int]
    prev_rank: Optional[int]      # previous ranking position
    uci_points: float
    top20_points: Optional[float] # points from top 20 riders (WT license calc)


@dataclass
class RiderRankingEntry:
    season: int
    team_slug: str
    rider_name: str
    pcs_slug: str
    uci_ranking_position: int
    uci_points: float


def scrape_team_ranking(season: int = CURRENT_SEASON) -> list[TeamRankingEntry]:
    """
    Scrape the UCI ProTeam ranking page for a given season.
    Returns entries for all teams (we filter to tracked teams).
    """
    entries = []
    try:
        url = "rankings/me/teams"
        data = Ranking(url).parse()

        for row in data.get("team_ranking", []):
            team_url = row.get("team_url", "")
            team_slug_full = team_url.split("/")[-1] if team_url else ""
            # Strip season suffix: "unibet-rose-rockets-2026" -> "unibet-rose-rockets"
            team_slug = "-".join(team_slug_full.split("-")[:-1]) if team_slug_full else team_slug_full

            entries.append(TeamRankingEntry(
                season=season,
                team_name=row.get("team_name", "").strip(),
                team_slug=team_slug,
                team_class=row.get("class", ""),
                uci_ranking_position=row.get("rank"),
                prev_rank=row.get("prev_rank"),
                uci_points=float(row.get("points") or 0),
                top20_points=None,
            ))
    except Exception as e:
        logger.error(f"Failed to scrape team ranking for {season}: {e}")

    return entries


def scrape_three_year_ranking(current_season: int = CURRENT_SEASON) -> dict:
    """
    Build a 3-year rolling ranking summary for tracked teams.
    Scrapes the last 3 seasons and aggregates points.
    Returns a dict with per-season and rolling totals.
    """
    seasons = [current_season, current_season - 1, current_season - 2]
    results = {}

    for season in seasons:
        logger.info(f"Fetching team ranking for {season}...")
        entries = scrape_team_ranking(season)
        for entry in entries:
            slug = entry.team_slug
            if slug not in results:
                results[slug] = {
                    "team_name": entry.team_name,
                    "team_slug": slug,
                    "seasons": {},
                    "three_year_total": 0,
                }
            results[slug]["seasons"][season] = {
                "position": entry.uci_ranking_position,
                "points": entry.uci_points,
            }
            results[slug]["three_year_total"] += entry.uci_points

    # Sort by 3-year total
    sorted_results = sorted(results.values(), key=lambda x: x["three_year_total"], reverse=True)
    return sorted_results


def scrape_tracked_teams_ranking(season: int = CURRENT_SEASON) -> list[TeamRankingEntry]:
    """Filter team ranking to only tracked teams."""
    tracked_slugs = {t["slug"] for t in TRACKED_TEAMS}
    all_entries = scrape_team_ranking(season)
    return [e for e in all_entries if e.team_slug in tracked_slugs]


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Scrape UCI team ranking")
    parser.add_argument("--season", type=int, default=CURRENT_SEASON)
    parser.add_argument("--three-year", action="store_true", help="Show 3-year rolling ranking")
    args = parser.parse_args()

    if args.three_year:
        print(f"\n3-Year Rolling UCI Team Ranking (up to {args.season})\n{'='*65}")
        rankings = scrape_three_year_ranking(args.season)

        # Find our tracked teams
        tracked_slugs = {t["slug"] for t in TRACKED_TEAMS}

        for i, team in enumerate(rankings[:30]):  # show top 30
            marker = " ◄ ROCKETS" if team["team_slug"] in tracked_slugs else ""
            seasons_str = "  ".join(
                f"{s}: {team['seasons'].get(s, {}).get('points', 0):.0f}pts (#{team['seasons'].get(s, {}).get('position', '?')})"
                for s in sorted(team["seasons"].keys(), reverse=True)
            )
            print(f"  {i+1:>3}. {team['team_name']:<35} Total: {team['three_year_total']:.0f}{marker}")
            print(f"       {seasons_str}")
    else:
        print(f"\nUCI ProTeam Ranking — {args.season}\n{'='*55}")
        entries = scrape_team_ranking(args.season)
        tracked_slugs = {t["slug"] for t in TRACKED_TEAMS}

        for e in entries[:30]:
            marker = " ◄" if e.team_slug in tracked_slugs else ""
            print(f"  #{e.uci_ranking_position or '?':>3}  {e.team_name:<35} {e.uci_points:.0f} pts{marker}")