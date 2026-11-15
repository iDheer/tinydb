# test_report.md: issue #3

## Attempt 1: PASSED

- Full suite: 240 passed, 0 failed, 0 errors, 0 skipped
- New tests (tests/test_autose_issue_3.py): 12

| Acceptance criterion | Tests |
|---|---|
| FR-SRCH-001.AC-1 | test_fr_srch_001_ac_1_limit_length |
| FR-SRCH-001.AC-2 | test_fr_srch_001_ac_2_limit_with_cached_query |
| FR-SRCH-001.AC-3 | test_fr_srch_001_ac_3_limit_one |
| FR-SRCH-002.AC-1 | test_fr_srch_002_ac_1_order |
| FR-SRCH-002.AC-2 | test_fr_srch_002_ac_2_prefix_of_unlimited |
| FR-SRCH-003.AC-1 | test_fr_srch_003_ac_1_unlimited |
| FR-SRCH-003.AC-2 | test_fr_srch_003_ac_2_fresh_list |
| FR-SRCH-004.AC-1 | test_fr_srch_004_ac_1_limited_does_not_poison_cache |
| FR-SRCH-005.AC-1 | test_fr_srch_005_ac_1_limit_larger_than_matches |
| FR-SRCH-005.AC-2 | test_fr_srch_005_ac_2_limit_equal_matches |
| FR-SRCH-006.AC-1 | test_fr_srch_006_ac_1_db_limit |
| FR-SRCH-006.AC-2 | test_fr_srch_006_ac_2_db_unlimited |

- On the base commit, 9 of 12 new tests fail (at least one must fail, so the tests exercise the change).

