# test_report.md: issue #4

## Attempt 1: PASSED

- Full suite: 235 passed, 0 failed, 0 errors, 0 skipped
- New tests (tests/test_autose_issue_4.py): 7

| Acceptance criterion | Tests |
|---|---|
| FR-OPS-001.AC-1 | test_fr_ops_001_ac_1_append_to_existing_list |
| FR-OPS-001.AC-2 | test_fr_ops_001_ac_2_only_matching_changed |
| FR-OPS-001.AC-3 | test_fr_ops_001_ac_3_mutates_in_place |
| FR-OPS-001.AC-4 | test_fr_ops_001_ac_4_no_dedup |
| FR-OPS-002.AC-1 | test_fr_ops_002_ac_1_missing_field_db |
| FR-OPS-002.AC-2 | test_fr_ops_002_ac_2_missing_field_dict |
| FR-OPS-002.AC-3 | test_fr_ops_002_ac_3_mixed_documents |

- On the base commit, 7 of 7 new tests fail (at least one must fail, so the tests exercise the change).

