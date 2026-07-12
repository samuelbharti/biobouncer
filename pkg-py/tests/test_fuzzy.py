"""Offline coverage for the fuzzy suggester used in cache mode."""

from biobouncer._fuzzy import _bounded_levenshtein, fuzzy_index, fuzzy_suggest


def test_bounded_levenshtein_within_and_over_k():
    assert _bounded_levenshtein("TP52", "TP53", 2) == 1
    assert _bounded_levenshtein("KMT2E", "KMT2A", 2) == 1
    assert _bounded_levenshtein("abc", "abc", 2) == 0
    # C9ORF72 vs C9orf72 is three substitutions, past the bound.
    assert _bounded_levenshtein("C9ORF72", "C9orf72", 2) is None
    assert _bounded_levenshtein("short", "muchlongerword", 2) is None


def test_fuzzy_suggest_picks_nearest_or_none():
    index = fuzzy_index({"TP53", "EGFR", "KMT2A", "KMT2D", "BRCA2"})
    assert fuzzy_suggest("TP52", index, 2) == "TP53"
    assert fuzzy_suggest("EGFF", index, 2) == "EGFR"
    assert fuzzy_suggest("ZZZZZZ", index, 2) is None


def test_fuzzy_suggest_breaks_ties_by_code_point():
    index = fuzzy_index({"KMT2A", "KMT2D"})
    # KMT2E is one edit from both; the code-point-smallest wins.
    assert fuzzy_suggest("KMT2E", index, 2) == "KMT2A"
