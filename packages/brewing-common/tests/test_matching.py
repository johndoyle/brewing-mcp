"""
Tests for brewing-common fuzzy matching.
"""

import pytest
from brewing_common.matching import (
    match_string,
    match_objects,
    best_match,
    normalise_ingredient_name,
    find_canonical_name,
    suggest_ingredient_names,
)


class TestMatchString:
    """Tests for string fuzzy matching."""

    def test_exact_match(self):
        matches = match_string("Cascade", ["Cascade", "Centennial", "Citra"])
        assert len(matches) >= 1
        assert matches[0][0] == "Cascade"
        assert matches[0][1] == 1.0

    def test_fuzzy_match(self):
        matches = match_string("casade", ["Cascade", "Centennial", "Citra"])
        assert len(matches) >= 1
        assert matches[0][0] == "Cascade"
        assert matches[0][1] > 0.8

    def test_no_match_below_threshold(self):
        matches = match_string("xyz", ["Cascade", "Centennial", "Citra"], threshold=0.9)
        assert len(matches) == 0

    def test_empty_candidates(self):
        matches = match_string("Cascade", [])
        assert len(matches) == 0

    def test_empty_query(self):
        matches = match_string("", ["Cascade", "Centennial"])
        assert len(matches) == 0

    def test_limit(self):
        matches = match_string(
            "c",
            ["Cascade", "Centennial", "Citra", "Chinook", "Columbus"],
            threshold=0.1,
            limit=3,
        )
        assert len(matches) <= 3

    def test_word_order_tolerance(self):
        # token_sort_ratio should handle word order
        matches = match_string(
            "Otter Maris",
            ["Maris Otter", "Golden Promise", "Pearl"],
            threshold=0.7,
        )
        assert len(matches) >= 1
        assert "Maris Otter" in matches[0][0]


class TestMatchObjects:
    """Tests for object fuzzy matching."""

    def test_match_dicts(self):
        objects = [
            {"name": "Cascade", "alpha": 5.5},
            {"name": "Centennial", "alpha": 10.0},
            {"name": "Citra", "alpha": 12.0},
        ]
        matches = match_objects(
            "casade",
            objects,
            key=lambda x: x["name"],
        )
        assert len(matches) >= 1
        assert matches[0][0]["name"] == "Cascade"
        assert matches[0][0]["alpha"] == 5.5


class TestBestMatch:
    """Tests for best single match."""

    def test_best_match(self):
        result = best_match("casade", ["Cascade", "Centennial", "Citra"])
        assert result is not None
        assert result[0] == "Cascade"

    def test_no_best_match(self):
        result = best_match("xyz", ["Cascade", "Centennial"], threshold=0.9)
        assert result is None


class TestNormaliseIngredientName:
    """Tests for ingredient name normalisation."""

    def test_canonical_name(self):
        assert normalise_ingredient_name("cascade") == "cascade"

    def test_alias(self):
        assert normalise_ingredient_name("Safale US-05") == "us-05"
        assert normalise_ingredient_name("US05") == "us-05"

    def test_unknown_name(self):
        result = normalise_ingredient_name("Some Unknown Ingredient")
        assert result == "some unknown ingredient"

    def test_whitespace_handling(self):
        assert normalise_ingredient_name("  Cascade  ") == "cascade"


class TestFindCanonicalName:
    """Tests for canonical name lookup."""

    def test_exact_canonical(self):
        assert find_canonical_name("cascade") == "cascade"

    def test_alias_lookup(self):
        assert find_canonical_name("Safale US-05") == "us-05"

    def test_fuzzy_lookup(self):
        result = find_canonical_name("casade", threshold=0.85)
        assert result == "cascade"

    def test_no_match(self):
        result = find_canonical_name("xyz123")
        assert result is None


class TestSuggestIngredientNames:
    """Tests for ingredient name suggestions."""

    def test_suggestions(self):
        suggestions = suggest_ingredient_names("cas")
        assert "cascade" in suggestions

    def test_limit(self):
        suggestions = suggest_ingredient_names("c", limit=3)
        assert len(suggestions) <= 3

    def test_empty_query(self):
        suggestions = suggest_ingredient_names("")
        assert len(suggestions) == 0
