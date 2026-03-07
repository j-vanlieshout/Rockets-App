# scraper/teams.py
# Scrapes the rider roster for every team in TRACKED_TEAMS.

import logging
from dataclasses import dataclass, asdict
from typing import Optional

from pcs_scraper import get_page, team_path

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import TRACKED_TEAMS, CURRENT_SEASON

logger = logging.getLogger(__name__)


@dataclass
class RosterEntry:
    team_slug: str
    season: int
    rider_name: str
    rider_pcs_slug: str       # used to fetch the full rider profile
    nationality: Optional[str]
    age: Optional[int]
    role: Optional[str]       # e.g. "All rounder", "Sprinter", …


def scrape_team_roster(team_slug: str, season: int) -> list[RosterEntry]:
    """
    Scrape the rider list from a PCS team overview page.

    PCS team roster URL pattern:
        /team/{slug}-{year}/overview
    """
    path = team_path(team_slug, season, "overview")
    soup = get_page(path)

    riders: list[RosterEntry] = []

    # PCS lists riders in a <ul class="riderlist"> block
    rider_list = soup.find("ul", class_="riderlist")
    if not rider_list:
        logger.warning(f"No riderlist found for {team_slug} {season} — page structure may have changed.")
        return riders

    for li in rider_list.find_all("li"):
        a_tag = li.find("a", href=True)
        if not a_tag:
            continue

        href = a_tag["href"]                         # e.g. "rider/dylan-groenewegen"
        rider_slug = href.split("/")[-1]
        rider_name = a_tag.get_text(strip=True)

        # Nationality flag img alt text
        flag = li.find("span", class_="flag")
        nationality = flag["class"][1] if flag and len(flag["class"]) > 1 else None

        # Age, if shown inline
        age_span = li.find("span", class_="age")
        age = int(age_span.get_text(strip=True).strip("()")) if age_span else None

        # Rider role / specialty
        role_span = li.find("span", class_="ridertype")
        role = role_span.get_text(strip=True) if role_span else None

        riders.append(RosterEntry(
            team_slug=team_slug,
            season=season,
            rider_name=rider_name,
            rider_pcs_slug=rider_slug,
            nationality=nationality,
            age=age,
            role=role,
        ))

    logger.info(f"Found {len(riders)} riders for {team_slug} {season}")
    return riders


def scrape_all_teams(season: int = CURRENT_SEASON) -> dict[str, list[RosterEntry]]:
    """Scrape rosters for every team in config.TRACKED_TEAMS."""
    results = {}
    for team in TRACKED_TEAMS:
        slug = team["slug"]
        logger.info(f"Scraping roster: {team['name']} ({season})")
        results[slug] = scrape_team_roster(slug, season)
    return results


# ── Run directly for a quick test ─────────────────────────────────────────────
if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    all_rosters = scrape_all_teams()

    for team_slug, roster in all_rosters.items():
        print(f"\n{'='*60}")
        print(f"  {team_slug.upper()}  ({CURRENT_SEASON})  —  {len(roster)} riders")
        print(f"{'='*60}")
        for r in roster:
            nat = f"[{r.nationality}]" if r.nationality else ""
            age = f"age {r.age}" if r.age else ""
            role = r.role or ""
            print(f"  {r.rider_name:<30} {nat:<6} {age:<10} {role}")
