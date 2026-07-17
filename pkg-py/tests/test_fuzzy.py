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


def test_fuzzy_suggest_ignore_case_resolves_a_case_only_difference():
    index = fuzzy_index({"TP53", "CD53", "BRCA1", "C9orf72"})
    # Case sensitive, tp53 is two edits from both TP53 and CD53 and the
    # code-point tie-break picks the wrong gene, and brca1 is four edits from
    # BRCA1 and out of reach entirely.
    assert fuzzy_suggest("tp53", index, 2) == "CD53"
    assert fuzzy_suggest("brca1", index, 2) is None
    # Ignoring case, both resolve, and the snapshot's own spelling comes back.
    assert fuzzy_suggest("tp53", index, 2, ignore_case=True) == "TP53"
    assert fuzzy_suggest("brca1", index, 2, ignore_case=True) == "BRCA1"
    assert fuzzy_suggest("C9ORF72", index, 2, ignore_case=True) == "C9orf72"


def test_fuzzy_suggest_ignore_case_still_spends_the_budget_on_real_edits():
    index = fuzzy_index({"TP53", "CD52"})
    # A lowercase typo: case is free, so the one real edit resolves to TP53
    # rather than to CD52, which is two real edits away.
    assert fuzzy_suggest("tp52", index, 2, ignore_case=True) == "TP53"
    # Case being free does not make everything match.
    assert fuzzy_suggest("zzzzzz", index, 2, ignore_case=True) is None


def test_fuzzy_suggest_ignore_case_ties_break_on_the_original_spelling():
    index = fuzzy_index({"KMT2A", "KMT2D"})
    assert fuzzy_suggest("kmt2e", index, 2, ignore_case=True) == "KMT2A"
