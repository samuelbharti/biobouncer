# shared/corpus

Cross-language conformance cases, one `*.cases.jsonl` file per source. Both the R
and Python test suites load these cases and assert the same verdicts, which is
how the two implementations are kept in agreement.

The case format is described in `PLAN.md`, section 7. No corpus files are added
yet.
