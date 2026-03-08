# tests/test_sync.py
# Unit tests for sync helpers — no PCS network calls, no DB required.

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.sync import extract_class_from_name, clean_stage_name


# ── extract_class_from_name ────────────────────────────────────────────────────

class TestExtractClassFromName:
    def test_extracts_class_at_end(self):
        name, cls = extract_class_from_name("Clasica de Almeria (1.Pro)")
        assert name == "Clasica de Almeria"
        assert cls  == "1.Pro"

    def test_extracts_uwt_class(self):
        name, cls = extract_class_from_name("Tour de France (2.UWT)")
        assert name == "Tour de France"
        assert cls  == "2.UWT"

    def test_no_class_returns_original(self):
        name, cls = extract_class_from_name("Tour de France", fallback="2.UWT")
        assert name == "Tour de France"
        assert cls  == "2.UWT"

    def test_no_class_no_fallback(self):
        name, cls = extract_class_from_name("Tour de France")
        assert name == "Tour de France"
        assert cls  == ""

    def test_class_with_trailing_whitespace(self):
        name, cls = extract_class_from_name("Strade Bianche (1.UWT)  ")
        assert name == "Strade Bianche"
        assert cls  == "1.UWT"

    def test_parentheses_in_middle_not_extracted(self):
        # Only extracts from the END of the string
        name, cls = extract_class_from_name("GP (Ouest) France (1.1)")
        assert name == "GP (Ouest) France"
        assert cls  == "1.1"

    def test_empty_string(self):
        name, cls = extract_class_from_name("")
        assert name == ""
        assert cls  == ""


# ── clean_stage_name ──────────────────────────────────────────────────────────

class TestCleanStageName:
    def test_strips_stage_prefix(self):
        result = clean_stage_name("S3Stage 3 - Bessèges › Bessèges")
        assert "S3Stage" not in result
        assert "Bessèges" in result

    def test_strips_dash_prefix(self):
        result = clean_stage_name("Race prefix - Actual Race Name")
        assert result == "Actual Race Name"

    def test_plain_name_unchanged(self):
        result = clean_stage_name("Paris-Roubaix")
        assert result == "Paris-Roubaix"

    def test_empty_string(self):
        result = clean_stage_name("")
        assert result == ""

    def test_strips_leading_whitespace(self):
        result = clean_stage_name("  Tour de Wallonie")
        assert result == "Tour de Wallonie"