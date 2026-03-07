# scraper/uci_points.py
# Scrapes UCI points per rider for all tracked teams and aggregates
# them into a team-level summary.
#
# Two data sources:
#   1. RiderResults  — full season results per rider, including uci_points per race
#   2. Ranking       — current UCI individual ranking (cross-check / ranking position)
#
# Run directly for a printed summary:
#   python uci_points.py
#   python uci_points.py --season 2025

import logging
import argparse
from dataclasses import dataclass
from typing import Optional

from procyclingstats import Rider, Ranking, Team

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import TRACKED_TEAMS, CURRENT_SEASON

logger = logging.getLogger(__name__)


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class RiderUCIResult:
    date: str
    race_name: str
    race_class: str          # e.g. "2.UWT", "1.Pro", "GT"
    stage_url: str
    position: Optional[int]
    uci_points: float


@dataclass
class RiderUCISummary:
    rider_name: str
    pcs_slug: str
    nationality: str
    age: int
    total_uci_points: float
    uci_ranking_position: Optional[int]   # from live UCI ranking page
    results: list[RiderUCIResult]         # individual race contributions


@dataclass
class TeamUCISummary:
    team_name: str
    team_slug: str
    season: int
    total_uci_points: float
    riders: list[RiderUCISummary]         # sorted by total_uci_points desc


# ── Scraping ───────────────────────────────────────────────────────────────────

def scrape_rider_uci_points(pcs_slug: str, season: int) -> tuple[float, list[RiderUCIResult]]:
    """
    Fetch a rider's season results and return (total_uci_points, [RiderUCIResult]).
    Uses Rider at rider/{slug}/{season} which returns season_results including uci_points.
    """
    url = f"rider/{pcs_slug}/{season}"
    try:
        data = Rider(url).parse()
    except (Exception, IndexError) as e:
        if "list index out of range" in str(e):
            logger.info(f"  No results yet for {pcs_slug} in {season}")
        else:
            logger.warning(f"  Could not fetch results for {pcs_slug}: {e}")
        return 0.0, []

    results = []
    total = 0.0

    for r in data.get("season_results", []):
        uci_pts = float(r.get("uci_points") or 0)
        total += uci_pts
        results.append(RiderUCIResult(
            date=r.get("date", ""),
            race_name=r.get("stage_name", ""),
            race_class=r.get("class", ""),
            stage_url=r.get("stage_url", ""),
            position=r.get("result"),
            uci_points=uci_pts,
        ))

    # Keep only races where UCI points were actually earned, sorted best first
    scored = sorted(
        [r for r in results if r.uci_points > 0],
        key=lambda x: x.uci_points,
        reverse=True,
    )

    return total, scored


def scrape_uci_ranking_positions(team_slug: str, season: int) -> dict[str, int]:
    """
    Fetch the current UCI individual ranking and return a dict of
    {pcs_rider_slug: ranking_position} for riders on this team.
    """
    positions = {}
    try:
        url = f"rankings/me/uci-individual?date={season}-12-31&filter=teams&teamId={team_slug}-{season}"
        ranking_data = Ranking(f"rankings/me/uci-individual").individual_ranking()
        for entry in ranking_data:
            rider_url = entry.get("rider_url", "")
            slug = rider_url.split("/")[-1]
            positions[slug] = entry.get("rank")
    except Exception as e:
        logger.warning(f"Could not fetch UCI ranking: {e}")
    return positions


def scrape_team_uci_points(team_slug: str, team_name: str, season: int) -> TeamUCISummary:
    """
    For a given team, scrape UCI points for every rider on the roster
    and return a full TeamUCISummary.
    """
    logger.info(f"Fetching roster: {team_name} ({season})")
    team_data = Team(f"team/{team_slug}-{season}").parse()
    roster = team_data.get("riders", [])

    # Get UCI ranking positions for cross-referencing
    ranking_positions = scrape_uci_ranking_positions(team_slug, season)

    rider_summaries = []
    for r in roster:
        slug = r["rider_url"].split("/")[-1]
        name = r["rider_name"]
        logger.info(f"  Fetching UCI points: {name}")

        total, results = scrape_rider_uci_points(slug, season)

        rider_summaries.append(RiderUCISummary(
            rider_name=name,
            pcs_slug=slug,
            nationality=r.get("nationality", ""),
            age=r.get("age", 0),
            total_uci_points=total,
            uci_ranking_position=ranking_positions.get(slug),
            results=results,
        ))

    # Sort riders by UCI points, highest first
    rider_summaries.sort(key=lambda x: x.total_uci_points, reverse=True)
    team_total = sum(r.total_uci_points for r in rider_summaries)

    return TeamUCISummary(
        team_name=team_name,
        team_slug=team_slug,
        season=season,
        total_uci_points=team_total,
        riders=rider_summaries,
    )


def scrape_all_teams_uci(season: int = CURRENT_SEASON) -> list[TeamUCISummary]:
    """Scrape UCI points for all teams in config.TRACKED_TEAMS."""
    summaries = []
    for team in TRACKED_TEAMS:
        summaries.append(scrape_team_uci_points(team["slug"], team["name"], season))
    return summaries


# ── Pretty-print helpers ───────────────────────────────────────────────────────

def print_team_summary(summary: TeamUCISummary):
    print(f"\n{'='*70}")
    print(f"  {summary.team_name}  —  {summary.season}  |  Total UCI pts: {summary.total_uci_points:.0f}")
    print(f"{'='*70}")
    print(f"  {'RIDER':<35} {'NAT':<5} {'AGE':<5} {'UCI PTS':<10} TOP RESULT")
    print(f"  {'-'*68}")

    for rider in summary.riders:
        top = rider.results[0] if rider.results else None
        top_str = f"P{top.position} {top.race_name[:25]} ({top.uci_points:.0f} pts)" if top else "—"
        print(f"  {rider.rider_name:<35} {rider.nationality:<5} {rider.age:<5} {rider.total_uci_points:<10.0f} {top_str}")

    print(f"\n  Top 10 riders contribute: "
          f"{sum(r.total_uci_points for r in summary.riders[:10]):.0f} / {summary.total_uci_points:.0f} pts")


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Scrape UCI points for tracked teams")
    parser.add_argument("--season", type=int, default=CURRENT_SEASON, help="Season year (default: current)")
    parser.add_argument("--rider", type=str, help="Print detailed breakdown for a single rider slug")
    args = parser.parse_args()

    if args.rider:
        # Detailed view for one rider
        total, results = scrape_rider_uci_points(args.rider, args.season)
        print(f"\n{args.rider}  —  {args.season}  |  Total UCI pts: {total:.0f}\n")
        print(f"  {'DATE':<12} {'CLASS':<8} {'POS':<6} {'UCI PTS':<10} RACE")
        print(f"  {'-'*65}")
        for r in results:
            print(f"  {r.date:<12} {r.race_class:<8} {str(r.position):<6} {r.uci_points:<10.0f} {r.race_name}")
    else:
        # Full team summary
        all_summaries = scrape_all_teams_uci(args.season)
        for summary in all_summaries:
            print_team_summary(summary)