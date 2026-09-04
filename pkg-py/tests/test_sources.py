"""The shared source specs must be usable by all three engines.

The specs are data, and nothing validates them at load time. A malformed
normalize block would surface as a different suggestion per language, or an
error in one of them, and only for the inputs that reach it. These checks fail
early instead.
"""

import biobouncer
from biobouncer._registry import get_source


def test_normalize_blocks_are_well_formed():
    for key in biobouncer.sources():
        source = get_source(key)
        norm = source.normalize
        if not norm:
            continue
        assert norm.get("case") in ("upper", "lower"), key
        prefix = norm.get("keep_prefix")
        if prefix is not None:
            assert isinstance(prefix, str), key
            assert prefix, key
            # The prefix is literal text the pattern must accept as written.
            assert source.curie is None, key
