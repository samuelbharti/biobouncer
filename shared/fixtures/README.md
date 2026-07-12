# Remote fixtures

Recorded responses for `remote` mode so the default test suite stays offline.

Layout: `remote/<resolver>/<subkey>/<id>.json`, where the id has its colon
replaced by an underscore. The subkey groups ids within a resolver:

- `ols`: the ontology, for example `remote/ols/mondo/MONDO_0005148.json`.
- `ensembl`: the constant `id`, for example `remote/ensembl/id/ENSG00000139618.json`.
- `uniprot`: the constant `uniprotkb`, for example `remote/uniprot/uniprotkb/P01308.json`.

Each file is a distilled transport response. Only `status` and `body` are read;
`url` and `recorded` record where and when the response came from.

```json
{"resolver": "ols", "url": "...", "recorded": "2026-07-09",
 "status": 200, "body": {"page": {"totalElements": 1}}}
```

Existence is decided per resolver:

- `ols`: present is `status` 200 with `body.page.totalElements` at least 1;
  absent is `status` 404. A present term that is obsolete has
  `body._embedded.terms[0].is_obsolete` true, and its successor (when any) is in
  `term_replaced_by` as a short form or a full IRI; such a term is invalid with
  the successor as its suggestion.
- `ensembl`: present is `status` 200; absent is `status` 400. The body is not read.
- `uniprot`: a present entry is `status` 200 with `body.entryType` starting with
  `UniProtKB`; a retired entry is `status` 200 with `entryType` `Inactive`. A
  `status` 404 is treated as absent. `body.organism.taxonId` is used for the
  remote species check.

When a `species` is requested, remote mode also checks it: Ensembl from the id
prefix (offline), UniProt from the entry's organism taxon id.

Both packages load these through the same transport seam they use for live
requests, so a fixture exercises the real existence logic. Live requests are
opt-in through the `BIOBOUNCER_REMOTE_TESTS` environment variable.
