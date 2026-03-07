# scraper/pcs_scraper.py
# Thin wrapper around the `procyclingstats` library.
# Handles season-aware URL building and shared helpers.

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CURRENT_SEASON


def team_url(slug: str, season: int = CURRENT_SEASON) -> str:
    """Build a PCS team URL, e.g. 'team/unibet-rose-rockets-2026'"""
    return f"team/{slug}-{season}"


def rider_url(slug: str) -> str:
    """Build a PCS rider URL, e.g. 'rider/dylan-groenewegen'"""
    return f"rider/{slug}"