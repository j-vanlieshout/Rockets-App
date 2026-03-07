# scraper/teams.py
# Scrapes the rider roster for every team in TRACKED_TEAMS
# using the `procyclingstats` library.

import logging
from dataclasses import dataclass
from typing import Optional

from procyclingstats import Team

from pcs_scraper import team_url

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import TRACKED_TEAMS, CURRENT_SEASON

logger = logging.getLogger(__name__)


@dataclass
class TeamInfo:
    slug: str
    season: int
    name: str
    abbreviation: str
    nationality: str
    status: str           # e.g. "PRT" (ProTeam), "WT" (WorldTour)
    pcs_points: int
    pcs_ranking: Optional[int]
    wins_count: int
    bike: Optional[str]


@dataclass
class RosterEntry:
    team_slug: str
    season: int
    rider_name: str
    rider_pcs_slug: str
    nationality: str
    age: int
    ranking_points: int
    ranking_position: int
    career_points: int


def scrape_team(team_slug: str, season: int = CURRENT_SEASON) -> tuple[TeamInfo, list[RosterEntry]]:
    """
    Scrape team info + full roster for a given team and season.
    Returns a (TeamInfo, [RosterEntry]) tuple.
    """
    url = team_url(team_slug, season)
    logger.info(f"Fetching team: {url}")
    data = Team(url).parse()

    info = TeamInfo(
        slug=team_slug,
        season=season,
        name=data["name"],
        abbreviation=data["abbreviation"],
        nationality=data["nationality"],
        status=data["status"],
        pcs_points=data["pcs_points"],
        pcs_ranking=data.get("pcs_ranking_position"),
        wins_count=data["wins_count"],
        bike=data.get("bike"),
    )

    roster = []
    for r in data["riders"]:
        # rider_url is like "rider/dylan-groenewegen" — extract the slug
        rider_slug = r["rider_url"].split("/")[-1]
        roster.append(RosterEntry(
            team_slug=team_slug,
            season=season,
            rider_name=r["rider_name"],
            rider_pcs_slug=rider_slug,
            nationality=r["nationality"],
            age=r["age"],
            ranking_points=r["ranking_points"],
            ranking_position=r["ranking_position"],
            career_points=r["career_points"],
        ))

    logger.info(f"  → {len(roster)} riders found")
    return info, roster


def scrape_all_teams(season: int = CURRENT_SEASON) -> dict[str, tuple[TeamInfo, list[RosterEntry]]]:
    """Scrape all teams listed in config.TRACKED_TEAMS."""
    results = {}
    for team in TRACKED_TEAMS:
        slug = team["slug"]
        results[slug] = scrape_team(slug, season)
    return results


# ── Run directly for a quick test ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    all_teams = scrape_all_teams()

    for slug, (info, roster) in all_teams.items():
        print(f"\n{'='*65}")
        print(f"  {info.name}  ({info.season})  |  {info.status}  |  PCS pts: {info.pcs_points}  |  Wins: {info.wins_count}")
        print(f"{'='*65}")
        print(f"  {'RIDER':<35} {'NAT':<5} {'AGE':<5} {'RNK PTS':<10} {'CAREER PTS'}")
        print(f"  {'-'*63}")
        for r in sorted(roster, key=lambda x: x.ranking_points, reverse=True):
            print(f"  {r.rider_name:<35} {r.nationality:<5} {r.age:<5} {r.ranking_points:<10} {r.career_points}")