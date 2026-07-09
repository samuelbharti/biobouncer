# Remote fixtures

Recorded responses for `remote` mode so the default test suite stays offline.

Layout: `remote/<resolver>/<key>/<id>.json`, where the id has its colon
replaced by an underscore. For the OLS resolver the key is the ontology, so
`remote/ols/mondo/MONDO_0005148.json` answers a lookup of `MONDO:0005148` in
`mondo`.

Each file is a distilled transport response:

```json
{"resolver": "ols", "url": "...", "recorded": "2026-07-09",
 "status": 200, "body": {"page": {"totalElements": 1}}}
```

Only `status` and `body` are read. A present term is `status` 200 with
`body.page.totalElements` at least 1. An absent term is `status` 404 with a
null body. The `url` and `recorded` fields record where and when the response
came from.

Both packages load these through the same transport seam they use for live
requests, so a fixture exercises the real parsing and existence logic. Live
requests are opt-in through the `BIOGATE_REMOTE_TESTS` environment variable.
