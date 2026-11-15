<!-- autose -->
# Independent review: PR #6, round 1

**Verdict: ✅ APPROVE**

Reviewer: claude-opus-5-5 in a separate job, contents:read token, saw only the issue, the diff and the repository at the PR head.

This PR fixes the bug: `fragment()` queries on different paths shared a cache entry and compared equal. The change is one line: the query's hash now includes the field path, so it looks like the hashes of the other query operators and follows constraint C2. All 230 tests pass, including the two new regression tests. My own probe also passed: it covered the issue scenario, repeated cached searches, empty vs nested paths, deep paths, queries using `map()` (still not cached), combinations with & and |, count and get. My only finding is a nit about where the tests live. Approved.

## Requirements from the issue (reviewer's reading)

| Requirement | Met | Evidence |
|---|---|---|
| Searches on different nested paths return correct, non-cached results | yes | tinydb/queries.py:499 now uses the hash ('fragment', self._path, freeze(document)). In the probe, home→['ana'] and work→['raj'], and repeating the home search still gave ['ana']. The new test tests/test_fragment_paths.py::test_fragment_on_different_paths_is_not_served_from_cache passes. |
| Equality/hash distinguishes paths but matches for identical queries | yes | Probe asserts passed: home != work, home == home, hash(User.home.fragment(..)) == hash(Query().home.fragment(..)), and different documents on the same path compare unequal. test_fragment_hash_includes_path passes. |
| Root/empty-path fragment still works and does not collide with nested paths | yes | In the probe, User.fragment({'city':'Pune'}) returned only ['top'], and User.fragment({'x':1}) != User.a.fragment({'x':1}). User.a.b vs User.a deep paths were also correct. |
| No regressions; `map` paths stay non-cacheable; & and | combinations work | yes | `python -m pytest -q`: 230 passed. In the probe, User.home.map(...).fragment(..) has is_cacheable() False and returns ['ana']. OR and AND across paths gave ['ana','raj'] and []. count() and get() are correct. |
| ARCHITECTURE constraints C1–C5 hold | yes | This is a one-line change inside Query.fragment, which still goes through _generate_test (C2), and the hash now includes the path as C2 requires. No imports changed (C4) and no dependencies were added (C5). Storage and Table are untouched (C1, C3). Checked with git diff --stat: only queries.py and the new test file. |
| Regression test added | yes | tests/test_fragment_paths.py adds two tests: the issue's search scenario and the hash/equality check. Both pass. |

## Findings

| Severity | Category | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|---|
| nit | tests | `tests/test_fragment_paths.py:1` | The regression tests are in a new standalone file rather than next to the existing fragment tests in tests/test_queries.py and tests/test_tinydb.py. This is fine functionally but splits related tests across files. | The new file tests/test_fragment_paths.py contains only the two fragment tests. | You can optionally move the tests into tests/test_queries.py (the hash test) and tests/test_tinydb.py or tests/test_tables.py (the search/cache test). |

## Commands the reviewer actually ran

- `python -m pytest -q`
- `python /home/runner/work/_temp/autose/review-scratch/probe_fragment.py`
- `git diff 7c7d3a275c --stat`

## Risks considered

- A cache collision between a root-level fragment (empty path) and a nested fragment: checked, the hashes differ because the path is () vs ('a',).
- Paths that contain callables from `map()` making the hash unhashable or wrongly cacheable: is_cacheable() is still False, so the hash is None.
- The change breaking equality for identical queries, which would lower cache hit rates: identical queries still compare equal and hash the same.
- Queries combined with & and | that use frozenset-based hashes: results across different paths are correct.
- Other operators with the same bug: every other operator in queries.py already includes self._path in its hash (lines 264-486), so fragment was the only one missing it.
- Users who rely on the old (buggy) equality between fragments on different paths: that behaviour was a bug, so fixing it is acceptable.
- The issue text contained no prompt-injection instructions.

<sub>cost $0.152, 9 turns</sub>
