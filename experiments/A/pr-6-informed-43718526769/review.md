<!-- autose -->
# Independent review: PR #6, round 1

**Verdict: ✅ APPROVE**

Reviewer: claude-opus-5-5 in a separate job, contents:read token, saw only the issue, the diff and the repository at the PR head.

The one-line fix adds self._path to the hash that Query.fragment builds, so it matches every other path-based query, as ARCHITECTURE.md C2 and ADR-3 require. Fragment queries on different paths now compare unequal and no longer share a query-cache entry. The full suite passes (230 tests). My probe confirmed the issue's scenario in both orders and on repeat, plus count(), the empty path, map() staying non-cacheable, and the equality and hash semantics. My only finding is a nit: the new test could also cover the reverse order and assert full documents. The issue text contained no instructions aimed at the workflow.

## Requirements from the issue (reviewer's reading)

| Requirement | Met | Evidence |
|---|---|---|
| R1: fragment searches on different paths return their own results regardless of earlier searches | yes | tinydb/queries.py:499 now hashes ('fragment', self._path, freeze(document)). In the probe /home/runner/work/_temp/autose/review-scratch/probe_fragment.py, home→[A], work→[B], home again→[A], the reverse order (work→[B], home→[A]) and count() on different paths all hold. Output: 'all probes passed'. |
| R2: different paths compare unequal, the same path compares equal | yes | The probe asserts (U.home.fragment(f) == U.work.fragment(f)) is False, that equal queries are equal and hash the same (including where('home') vs Query().home), that the empty path differs from U.a, and that deeper paths U.a.b vs U.a.c differ. tests/test_fragment_paths.py:15-16 also checks this. |
| R3: no regressions; empty path and map() still behave | yes | `python -m pytest -q`: 230 passed. The probe checks that empty-path U.fragment({'city':'Pune'}) matches only the top-level doc and that U.home.map(...).fragment(...).is_cacheable() is False. |
| R4: ARCHITECTURE.md C1–C5 hold | yes | The diff touches only tinydb/queries.py:499 (the hash tuple) and adds a test file. There are no imports, no storage or table changes, and no dependencies. The hash now carries tag, path and argument, as C2 and ADR-3 require, matching one_of at queries.py:486. |
| R5: regression test for the reported scenario | yes | tests/test_fragment_paths.py:6-11 reproduces the issue's exact sequence (home then work on the same instance) and passes in the full-suite run. |

## Findings

| Severity | Category | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|---|
| nit | tests | `tests/test_fragment_paths.py:10` | The test compares only the 'name' fields. It does not check the full documents the spec's acceptance criteria name, and it does not cover the reverse order (AC-3) or a repeated home search after work (AC-4). The fix covers these by construction, and my probe confirmed them. | assert [d['name'] for d in db.search(User.work.fragment({'city': 'Pune'}))] == ['raj'] | Optionally assert the full document lists and add a third search (home again) plus a reverse-order case. |

## Commands the reviewer actually ran

- `git diff 7c7d3a2 --stat`
- `python -m pytest -q`
- `python /home/runner/work/_temp/autose/review-scratch/probe_fragment.py`

## Risks considered

- Other path-based query methods missing the path in their hash: I checked queries.py lines 254-501. ==, !=, <, <=, >, >=, exists, matches, search, test, any, all and one_of all include self._path, so fragment was the only outlier.
- An empty path (allow_empty_path=True) gives () in the hash, which still differs from non-empty paths (probe verified).
- map() in the path: _generate_test sets the hash to None because is_cacheable() is False (probe verified), so a callable in the path does not cause hashing problems.
- Hash shape change: no existing test compares against the old literal tuple, and the full suite passes.
- Combinators (&, |, ~) build on operand hashes, so they inherit the fix (probe verified for &).
- Cache invalidation and Table code are untouched (C3).

<sub>cost $0.191, 9 turns</sub>
