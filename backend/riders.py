# scraper/riders.py
# Scrapes detailed stats from an individual rider's PCS profile page.

import logging
import re
from dataclasses import dataclass
from typing import Optional

from pcs_scraper import get_page, rider_path

logger = logging.getLogger(__name__)


@dataclass
class RiderProfile:
    pcs_slug: str
    full_name: str
    nationality: Optional[str]
    date_of_birth: Optional[str]      # ISO format: YYYY-MM-DD
    age: Optional[int]
    weight_kg: Optional[int]
    height_cm: Optional[int]
    specialty: Optional[str]          # PCS specialty label, e.g. "Sprinter"
    pcs_ranking: Optional[int]        # Current PCS world ranking
    pcs_points: Optional[int]         # Current season PCS points
    team: Optional[str]
    profile_url: str


def scrape_rider(pcs_slug: str) -> Optional[RiderProfile]:
    """
    Scrape a full rider profile from PCS.

    PCS rider URL pattern:
        /rider/{slug}
    """
    path = rider_path(pcs_slug)
    try:
        soup = get_page(path)
    except Exception as e:
        logger.error(f"Failed to fetch rider {pcs_slug}: {e}")
        return None

    profile_url = f"https://www.procyclingstats.com/{path}"

    # ── Name ──────────────────────────────────────────────────────────────────
    name_tag = soup.find("h1")
    full_name = name_tag.get_text(strip=True) if name_tag else pcs_slug.replace("-", " ").title()

    # ── Info list (nationality, DoB, weight, height, team) ───────────────────
    nationality = date_of_birth = age = weight_kg = height_cm = team = specialty = None
    pcs_ranking = pcs_points = None

    info_div = soup.find("div", class_="rdr-info-cont")
    if info_div:
        text = info_div.get_text(" ", strip=True)

        if m := re.search(r"Date of birth:\s*([\d\-]+)", text):
            date_of_birth = m.group(1)
        if m := re.search(r"Age:\s*(\d+)", text):
            age = int(m.group(1))
        if m := re.search(r"Weight:\s*(\d+)", text):
            weight_kg = int(m.group(1))
        if m := re.search(r"Height:\s*(\d+)", text):
            height_cm = int(m.group(1))

        # Nationality from flag span
        flag = info_div.find("span", class_="flag")
        if flag and len(flag["class"]) > 1:
            nationality = flag["class"][1].upper()

        # Current team
        team_a = info_div.find("a", href=re.compile(r"^team/"))
        if team_a:
            team = team_a.get_text(strip=True)

    # ── Specialty / rider type ─────────────────────────────────────────────
    specialty_tag = soup.find("span", class_="rdrtype") or soup.find("div", class_="rdrtype")
    if specialty_tag:
        specialty = specialty_tag.get_text(strip=True)

    # ── PCS ranking & points ───────────────────────────────────────────────
    ranking_div = soup.find("div", class_="ranks")
    if ranking_div:
        if m := re.search(r"PCS ranking[^\d]*(\d+)", ranking_div.get_text()):
            pcs_ranking = int(m.group(1))
        if m := re.search(r"Points[^\d]*(\d+)", ranking_div.get_text()):
            pcs_points = int(m.group(1))

    return RiderProfile(
        pcs_slug=pcs_slug,
        full_name=full_name,
        nationality=nationality,
        date_of_birth=date_of_birth,
        age=age,
        weight_kg=weight_kg,
        height_cm=height_cm,
        specialty=specialty,
        pcs_ranking=pcs_ranking,
        pcs_points=pcs_points,
        team=team,
        profile_url=profile_url,
    )


# ── Run directly for a quick test ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    slug = sys.argv[1] if len(sys.argv) > 1 else "dylan-groenewegen"
    profile = scrape_rider(slug)

    if profile:
        from dataclasses import asdict
        import json
        print(json.dumps(asdict(profile), indent=2))
    else:
        print("Could not retrieve profile.")
