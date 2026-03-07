# scraper/riders.py
# Scrapes a full rider profile using the `procyclingstats` library.

import logging
from dataclasses import dataclass
from typing import Optional

from procyclingstats import Rider

from pcs_scraper import rider_url

logger = logging.getLogger(__name__)


@dataclass
class SeasonResult:
    date: str
    race_name: str
    stage_url: str
    position: Optional[int]
    gc_position: Optional[int]
    distance_km: float
    pcs_points: float
    uci_points: float


@dataclass
class RiderProfile:
    pcs_slug: str
    full_name: str
    nationality: str
    birthdate: str             # e.g. "1993-6-21"
    height_m: Optional[float]
    weight_kg: Optional[float]
    # Speciality points breakdown
    sp_one_day_races: int
    sp_gc: int
    sp_time_trial: int
    sp_sprint: int
    sp_climber: int
    sp_hills: int
    # Current season
    season_results: list[SeasonResult]


def scrape_rider(pcs_slug: str) -> Optional[RiderProfile]:
    """Scrape a full rider profile from PCS."""
    url = rider_url(pcs_slug)
    try:
        data = Rider(url).parse()
    except Exception as e:
        logger.error(f"Failed to fetch rider {pcs_slug}: {e}")
        return None

    sp = data.get("points_per_speciality", {})

    results = []
    for r in data.get("season_results", []):
        results.append(SeasonResult(
            date=r["date"],
            race_name=r["stage_name"],
            stage_url=r["stage_url"],
            position=r.get("result"),
            gc_position=r.get("gc_position"),
            distance_km=r.get("distance", 0),
            pcs_points=r.get("pcs_points", 0),
            uci_points=r.get("uci_points", 0),
        ))

    return RiderProfile(
        pcs_slug=pcs_slug,
        full_name=data["name"],
        nationality=data["nationality"],
        birthdate=data["birthdate"],
        height_m=data.get("height"),
        weight_kg=data.get("weight"),
        sp_one_day_races=sp.get("one_day_races", 0),
        sp_gc=sp.get("gc", 0),
        sp_time_trial=sp.get("time_trial", 0),
        sp_sprint=sp.get("sprint", 0),
        sp_climber=sp.get("climber", 0),
        sp_hills=sp.get("hills", 0),
        season_results=results,
    )


def dominant_specialty(profile: RiderProfile) -> str:
    """Return the rider's strongest specialty as a readable label."""
    specialties = {
        "One Day Races": profile.sp_one_day_races,
        "GC": profile.sp_gc,
        "Time Trial": profile.sp_time_trial,
        "Sprint": profile.sp_sprint,
        "Climber": profile.sp_climber,
        "Hills": profile.sp_hills,
    }
    return max(specialties, key=specialties.get)


# ── Run directly for a quick test ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    slug = sys.argv[1] if len(sys.argv) > 1 else "dylan-groenewegen"
    profile = scrape_rider(slug)

    if profile:
        print(f"\n{profile.full_name}  ({profile.nationality})")
        print(f"  Born:      {profile.birthdate}")
        print(f"  Height:    {profile.height_m}m   Weight: {profile.weight_kg}kg")
        print(f"  Specialty: {dominant_specialty(profile)}")
        print(f"\n  {'DATE':<12} {'RACE':<45} {'POS':<6} {'PCS PTS'}")
        print(f"  {'-'*70}")
        for r in profile.season_results:
            pos = str(r.position) if r.position else "DNS/DNF"
            print(f"  {r.date:<12} {r.race_name:<45} {pos:<6} {r.pcs_points}")
    else:
        print("Could not retrieve profile.")