"""The shared source specs must be usable by all three engines.

The specs are data, and nothing validates them at load time. A malformed
normalize rule would surface as a different suggestion per language, or an
error in one of them, and only for the inputs that reach the rule. These
checks fail early instead.
"""

import re

import biobouncer
from biobouncer._registry import get_source


def test_normalize_blocks_are_well_formed():
    for key in biobouncer.sources():
        norm = get_source(key).normalize
        if not norm:
            continue
        assert norm.get("case") in ("upper", "lower"), key
        for rule in norm.get("rewrite") or ():
            assert isinstance(rule.get("from"), str) and rule["from"], key
            assert isinstance(rule.get("to"), str), key
            re.compile(rule["from"])
