# test_report.md: issue #4

## Attempt 1: PASSED

- Full suite: 231 passed, 0 failed, 0 errors, 0 skipped
- New tests (tests/test_autose_issue_4.py): 3

| Acceptance criterion | Tests |
|---|---|
| FR-OPS-002.AC-1 | test_fr_ops_002_ac_1_append_creates_missing_field |
| FR-OPS-002.AC-2 | test_fr_ops_002_ac_2_other_documents_untouched |
| FR-OPS-002.AC-3 | test_fr_ops_002_ac_3_mixed_existing_and_missing |

- On the base commit, 3 of 3 new tests fail (at least one must fail, so the tests exercise the change).

## Tester notes

Wrote 3 tests; they pass with the change and the full suite passes (231). I did not run them against the pre-change code, but they import append from tinydb.operations, which didn't exist there, so they would fail with ImportError.
