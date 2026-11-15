<!-- autose -->
# Independent review: PR #12, round 1

**Verdict: ✅ APPROVE**

Reviewer: claude-opus-5-5 in a separate job, contents:read token, saw only the issue, the diff and the repository at the PR head.

I approve the PR. It fixes the bug with a one-line change at tinydb/queries.py:499: the fragment query's hash now includes the field path, as ARCHITECTURE.md C2 requires. Before, fragment queries on different fields hashed and compared as equal, so the table's query cache returned the first field's results for the second search. The full suite passes (232 tests). My own 5-test probe also passes: it covers the issue's example, equality and hashing, root-level versus nested fragments, edge cases, and confirms the cache is still used. My first attempt to run the probe as a plain script failed because tinydb wasn't importable from the scratch directory, so I reran it as a pytest file. Remaining findings: one minor (the new tests don't check the equality/hash symptom the issue reports) and one nit (an unused import and a test file named after the workflow).

## Requirements from the issue (reviewer's reading)

| Requirement | Met | Evidence |
|---|---|---|
| R1: second nested fragment search returns correct results | yes | Probe test_issue_repro passed: home->['ana'], work->['raj'] on the same db. PR tests test_fr_qry_001_ac_1..4 passed in the full suite run. |
| R2: different-path fragments are unequal; same-path fragments are equal with equal hashes | yes | tinydb/queries.py:499 now uses hashval ('fragment', self._path, freeze(document)). Probe test_equality_and_hash passed (home != work, home == home, hashes equal). |
| R3: root fragment still works and is distinct from nested | yes | Probe test_root_vs_nested_same_db passed. Query().fragment(d) != Query().home.fragment(d), and both return the correct documents from the same db. |
| R4: no regressions; cache still used | yes | `python -m pytest -q`: 232 passed. Probe test_cache_still_used passed (the query is a key in table._query_cache). Probe test_misc_edges passed: where(), count, missing field, AND-combination, deeper path a.b. |
| R5: C1–C5 hold, C2 in particular | yes | The diff changes one line in queries.py (hash tuple now includes the path, as C2 requires) and adds one test file. It adds no imports and changes nothing in storages.py, table.py or pyproject.toml. |

## Findings

| Severity | Category | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|---|
| minor | tests | `tests/test_autose_issue_1.py:1` | The new tests cover only search results. They do not check the equality and hash symptom from the issue (User.home.fragment(d) == User.work.fragment(d) was True), which is the actual root cause. | No assertion in tests/test_autose_issue_1.py compares the two QueryInstances or their hashes. My probe test_equality_and_hash covers this, and it passes. | Add a test (ideally in tests/test_queries.py next to the existing fragment tests) asserting Query().home.fragment(d) != Query().work.fragment(d), that same-path queries are equal with equal hashes, and that Query().fragment(d) != Query().home.fragment(d). |
| nit | tests | `tests/test_autose_issue_1.py:1` | The test file name refers to the workflow rather than the feature, and the `where` import is unused. | `from tinydb import TinyDB, where, Query`: `where` is never used. | Move the tests into tests/test_queries.py or tests/test_tables.py, or drop the unused import. |

## Commands the reviewer actually ran

- `python -m pytest -q`
- `python /home/runner/work/_temp/autose/review-scratch/probe_fragment.py`
- `python -m pytest -q -p no:cacheprovider --no-cov /home/runner/work/_temp/autose/review-scratch/test_probe_fragment.py`

## Risks considered

- Cache key collision between fragment queries on different paths (the root cause): fixed by including self._path in the hash.
- Empty path (allow_empty_path=True): self._path is () and the hash stays valid and hashable. The probe confirms root and nested queries are distinct.
- Paths containing callables (from map()): _path may contain functions, which are hashable. If the path is non-cacheable, is_cacheable() still returns None.
- freeze(document) for nested dicts in the fragment: unchanged from before.
- Hash changes for root-level fragment queries: only affects in-memory cache keys and is not persisted, so there is no compatibility risk.
- Other query methods missing the path in their hash: checked. All other _generate_test callers already include self._path.
- C4/C5 import layering and dependencies: untouched.

<sub>cost $0.232, 11 turns</sub>
