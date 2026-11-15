# test_report.md: issue #5

## Attempt 1: PASSED

- Full suite: 247 passed, 0 failed, 0 errors, 0 skipped
- New tests (tests/test_autose_issue_5.py): 19

| Acceptance criterion | Tests |
|---|---|
| FR-JSON-001.AC-1 | test_fr_json_001_ac_1_naive_datetime_roundtrip, test_fr_json_001_ac_1_custom_default_kwarg_still_used |
| FR-JSON-001.AC-2 | test_fr_json_001_ac_2_insert_datetime_no_error |
| FR-JSON-002.AC-1 | test_fr_json_002_ac_1_date_roundtrip, test_fr_json_002_ac_1_custom_cls_kwarg_still_used |
| FR-JSON-003.AC-1 | test_fr_json_003_ac_1_offset_aware_roundtrip |
| FR-JSON-003.AC-2 | test_fr_json_003_ac_2_utc_roundtrip |
| FR-JSON-003.AC-3 | test_fr_json_003_ac_3_naive_and_aware_distinct |
| FR-JSON-004.AC-1 | test_fr_json_004_ac_1_strings_stay_strings |
| FR-JSON-004.AC-2 | test_fr_json_004_ac_2_string_and_date_distinguished |
| FR-JSON-005.AC-1 | test_fr_json_005_ac_1_datetime_less_than_query |
| FR-JSON-005.AC-2 | test_fr_json_005_ac_2_date_ge_query |
| FR-JSON-005.AC-3 | test_fr_json_005_ac_3_aware_equality_query |
| CON-001.AC-1 | test_con_001_ac_1_no_runtime_dependencies |
| CON-001.AC-2 | test_con_001_ac_2_only_stdlib_imports |
| CON-002.AC-1 | test_con_002_ac_1_memory_storage_keeps_object |
| CON-002.AC-2 | test_con_002_ac_2_memory_storage_behaviour_unchanged |
| CON-003.AC-1 | test_con_003_ac_1_query_behaviour_on_plain_values |
| CON-003.AC-2 | test_con_003_ac_2_query_public_names_unchanged |

- On the base commit, 12 of 19 new tests fail (at least one must fail, so the tests exercise the change).

## Attempt 2: PASSED

- Full suite: 247 passed, 0 failed, 0 errors, 0 skipped
- New tests (tests/test_autose_issue_5.py): 19

| Acceptance criterion | Tests |
|---|---|
| FR-JSON-001.AC-1 | test_fr_json_001_ac_1_naive_datetime_roundtrip, test_fr_json_001_ac_1_custom_default_kwarg_still_used |
| FR-JSON-001.AC-2 | test_fr_json_001_ac_2_insert_datetime_no_error |
| FR-JSON-002.AC-1 | test_fr_json_002_ac_1_date_roundtrip, test_fr_json_002_ac_1_custom_cls_kwarg_still_used |
| FR-JSON-003.AC-1 | test_fr_json_003_ac_1_offset_aware_roundtrip |
| FR-JSON-003.AC-2 | test_fr_json_003_ac_2_utc_roundtrip |
| FR-JSON-003.AC-3 | test_fr_json_003_ac_3_naive_and_aware_distinct |
| FR-JSON-004.AC-1 | test_fr_json_004_ac_1_strings_stay_strings |
| FR-JSON-004.AC-2 | test_fr_json_004_ac_2_string_and_date_distinguished |
| FR-JSON-005.AC-1 | test_fr_json_005_ac_1_datetime_less_than_query |
| FR-JSON-005.AC-2 | test_fr_json_005_ac_2_date_ge_query |
| FR-JSON-005.AC-3 | test_fr_json_005_ac_3_aware_equality_query |
| CON-001.AC-1 | test_con_001_ac_1_no_runtime_dependencies |
| CON-001.AC-2 | test_con_001_ac_2_only_stdlib_imports |
| CON-002.AC-1 | test_con_002_ac_1_memory_storage_keeps_object |
| CON-002.AC-2 | test_con_002_ac_2_memory_storage_behaviour_unchanged |
| CON-003.AC-1 | test_con_003_ac_1_query_behaviour_on_plain_values |
| CON-003.AC-2 | test_con_003_ac_2_query_public_names_unchanged |

- On the base commit, 12 of 19 new tests fail (at least one must fail, so the tests exercise the change).

## Tester notes

The implementer's dispute was valid. The CON-001.AC-1 test imported tomllib unconditionally, and tomllib doesn't exist on Python 3.10. It now tries tomllib, then tomli, then falls back to a regex check of pyproject.toml for a non-empty `dependencies = [...]`. The full suite passes (247 passed, Python 3.12). I did not run it on 3.10. Only that one test was edited; the other tests are unchanged and listed in the earlier submission.
