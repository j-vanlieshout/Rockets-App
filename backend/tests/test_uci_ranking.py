# tests/test_uci_ranking.py
# Unit tests for the UCI ranking scraper — mocks PCS network calls.

import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper.uci_ranking import scrape_team_ranking, TeamRankingEntry


MOCK_RANKING_DATA = {
    "team_ranking": [
        {
            "team_name": "UAE Team Emirates",
            "team_url":  "team/uae-team-emirates-2026",
            "class":     "WT",
            "rank":      1,
            "prev_rank": 1,
            "points":    8500.0,
        },
        {
            "team_name": "Unibet Rose Rockets",
            "team_url":  "team/unibet-rose-rockets-2026",
            "class":     "PRT",
            "rank":      23,
            "prev_rank": 26,
            "points":    876.0,
        },
        {
            "team_name": "Team With No Points",
            "team_url":  "team/some-team-2026",
            "class":     "CT",
            "rank":      80,
            "prev_rank": None,
            "points":    None,      # PCS sometimes returns None instead of 0
        },
    ]
}


class TestScrapeTeamRanking:
    def _mock_ranking(self):
        mock = MagicMock()
        mock.parse.return_value = MOCK_RANKING_DATA
        return mock

    def test_returns_list_of_entries(self):
        with patch("scraper.uci_ranking.Ranking", return_value=self._mock_ranking()):
            entries = scrape_team_ranking(2026)
        assert isinstance(entries, list)
        assert len(entries) == 3

    def test_entry_fields_parsed_correctly(self):
        with patch("scraper.uci_ranking.Ranking", return_value=self._mock_ranking()):
            entries = scrape_team_ranking(2026)
        rockets = next(e for e in entries if "Rockets" in e.team_name)
        assert rockets.uci_ranking_position == 23
        assert rockets.prev_rank            == 26
        assert rockets.uci_points           == 876.0
        assert rockets.team_class           == "PRT"

    def test_year_suffix_stripped_from_slug(self):
        with patch("scraper.uci_ranking.Ranking", return_value=self._mock_ranking()):
            entries = scrape_team_ranking(2026)
        rockets = next(e for e in entries if "Rockets" in e.team_name)
        assert rockets.team_slug == "unibet-rose-rockets"
        assert "2026" not in rockets.team_slug

    def test_none_points_coerced_to_zero(self):
        with patch("scraper.uci_ranking.Ranking", return_value=self._mock_ranking()):
            entries = scrape_team_ranking(2026)
        no_points = next(e for e in entries if "No Points" in e.team_name)
        assert no_points.uci_points == 0.0

    def test_raises_on_pcs_failure(self):
        mock = MagicMock()
        mock.parse.side_effect = Exception("PCS unreachable")
        with patch("scraper.uci_ranking.Ranking", return_value=mock):
            with pytest.raises(Exception, match="PCS unreachable"):
                scrape_team_ranking(2026)

    def test_empty_ranking_returns_empty_list(self):
        mock = MagicMock()
        mock.parse.return_value = {"team_ranking": []}
        with patch("scraper.uci_ranking.Ranking", return_value=mock):
            entries = scrape_team_ranking(2026)
        assert entries == []