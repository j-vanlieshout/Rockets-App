# scraper/pcs_scraper.py
# Low-level helpers: fetch a PCS page, return a BeautifulSoup object.

import time
import logging
import requests
from bs4 import BeautifulSoup

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import PCS_BASE_URL, REQUEST_HEADERS, SCRAPE_DELAY_SECONDS

logger = logging.getLogger(__name__)


def get_page(path: str) -> BeautifulSoup:
    """
    Fetch a PCS page by its relative path (e.g. '/team/unibet-rose-rockets-2026')
    and return a parsed BeautifulSoup object.

    Raises requests.HTTPError on non-2xx responses.
    """
    url = f"{PCS_BASE_URL}/{path.lstrip('/')}"
    logger.info(f"Fetching: {url}")

    response = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
    response.raise_for_status()

    time.sleep(SCRAPE_DELAY_SECONDS)   # polite delay between requests
    return BeautifulSoup(response.text, "html.parser")


def team_path(slug: str, season: int, page: str = "overview") -> str:
    """Build the PCS relative path for a team page."""
    return f"team/{slug}-{season}/{page}"


def rider_path(slug: str) -> str:
    """Build the PCS relative path for a rider profile page."""
    return f"rider/{slug}"
