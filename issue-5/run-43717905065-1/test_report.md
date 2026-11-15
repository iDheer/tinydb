# test_report.md: issue #5

## Attempt 1: PASSED

- Full suite: 245 passed, 0 failed, 0 errors, 0 skipped
- New tests (tests/test_autose_issue_5.py): 17

| Acceptance criterion | Tests |
|---|---|
| FR-JSON-001.AC-1 | test_fr_json_001_ac_1_naive_datetime_roundtrip |
| FR-JSON-001.AC-2 | test_fr_json_001_ac_2_insert_datetime_no_error |
| FR-JSON-002.AC-1 | test_fr_json_002_ac_1_date_roundtrip |
| FR-JSON-003.AC-1 | test_fr_json_003_ac_1_offset_aware_roundtrip |
| FR-JSON-003.AC-2 | test_fr_json_003_ac_2_utc_roundtrip |
| FR-JSON-003.AC-3 | test_fr_json_003_ac_3_naive_and_aware_distinct |
| FR-JSON-004.AC-1 | test_fr_json_004_ac_1_strings_stay_strings |
| FR-JSON-004.AC-2 | test_fr_json_004_ac_2_string_and_date_distinguished |
| FR-JSON-005.AC-1 | test_fr_json_005_ac_1_datetime_less_than_query |
| FR-JSON-005.AC-2 | test_fr_json_005_ac_2_date_ge_query |
| FR-JSON-005.AC-3 | test_fr_json_005_ac_3_aware_equality_query |
| CON-001.AC-1 | test_con_001_ac_1_no_new_runtime_dependencies |
| CON-001.AC-2 | test_con_001_ac_2_only_stdlib_imports |
| CON-002.AC-1 | test_con_002_ac_1_memory_storage_keeps_object |
| CON-002.AC-2 | test_con_002_ac_2_memory_storage_unchanged |
| CON-003.AC-1 | test_con_003_ac_1_queries_unchanged |
| CON-003.AC-2 | test_con_003_ac_2_query_public_names_unchanged |

- On the base commit, 10 of 17 new tests fail (at least one must fail, so the tests exercise the change).

## Attempt 2: PASSED

- Full suite: 245 passed, 0 failed, 0 errors, 0 skipped
- New tests (tests/test_autose_issue_5.py): 17

| Acceptance criterion | Tests |
|---|---|
| FR-JSON-001.AC-1 | test_fr_json_001_ac_1_naive_datetime_roundtrip |
| FR-JSON-001.AC-2 | test_fr_json_001_ac_2_insert_datetime_no_error |
| FR-JSON-002.AC-1 | test_fr_json_002_ac_1_date_roundtrip |
| FR-JSON-003.AC-1 | test_fr_json_003_ac_1_offset_aware_roundtrip |
| FR-JSON-003.AC-2 | test_fr_json_003_ac_2_utc_roundtrip |
| FR-JSON-003.AC-3 | test_fr_json_003_ac_3_naive_and_aware_distinct |
| FR-JSON-004.AC-1 | test_fr_json_004_ac_1_strings_stay_strings |
| FR-JSON-004.AC-2 | test_fr_json_004_ac_2_string_and_date_distinguished |
| FR-JSON-005.AC-1 | test_fr_json_005_ac_1_datetime_less_than_query |
| FR-JSON-005.AC-2 | test_fr_json_005_ac_2_date_ge_query |
| FR-JSON-005.AC-3 | test_fr_json_005_ac_3_aware_equality_query |
| CON-001.AC-1 | test_con_001_ac_1_no_new_runtime_dependencies |
| CON-001.AC-2 | test_con_001_ac_2_only_stdlib_imports |
| CON-002.AC-1 | test_con_002_ac_1_memory_storage_keeps_object |
| CON-002.AC-2 | test_con_002_ac_2_memory_storage_unchanged |
| CON-003.AC-1 | test_con_003_ac_1_queries_unchanged |
| CON-003.AC-2 | test_con_003_ac_2_query_public_names_unchanged |

- On the base commit, 10 of 17 new tests fail (at least one must fail, so the tests exercise the change).

## Tester notes

The implementer's complaint was valid: the test file imported tomllib at top level, which only exists on Python 3.11+ and breaks collection on 3.10. I removed the import. The CON-001.AC-1 test now reads the `dependencies = [...]` list from pyproject.toml with a regex, for both the working tree and the base commit. A missing list counts as empty, and the test still asserts that the new list has no entry the old one lacks. All other tests are unchanged. The full suite passes on Python 3.12 (245 passed), including all 17 tests in tests/test_autose_issue_5.py. I did not run it on 3.10.
