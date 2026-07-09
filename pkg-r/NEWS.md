# biogate 0.0.0.9000

* `check_id()` and `is_valid_id()` implement offline `pattern` mode for an
  initial set of sources (mondo, efo, go, chebi, ensembl, uniprot).
* `sources()` and `source_info()` list what can be checked.
* Arguments are validated with checkmate, errors are raised with cli and carry a
  condition class, and `check_id()` returns a tibble.
* Initial package scaffold.
