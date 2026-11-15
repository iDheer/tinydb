# test_report.md: issue #2

## Attempt 1: PASSED

- Full suite: 234 passed, 0 failed, 0 errors, 0 skipped
- New tests (tests/test_autose_issue_2.py): 6

| Acceptance criterion | Tests |
|---|---|
| FR-QUERY-001.AC-1 | test_fr_query_001_ac_1_generator_search |
| FR-QUERY-001.AC-2 | test_fr_query_001_ac_2_generator_direct_calls |
| FR-QUERY-001.AC-3 | test_fr_query_001_ac_3_generator_count |
| FR-QUERY-002.AC-1 | test_fr_query_002_ac_1_list_search |
| FR-QUERY-002.AC-2 | test_fr_query_002_ac_2_list_direct_calls |
| FR-QUERY-002.AC-3 | test_fr_query_002_ac_3_list_reused |

- On the base commit, 3 of 6 new tests fail (at least one must fail, so the tests exercise the change).

