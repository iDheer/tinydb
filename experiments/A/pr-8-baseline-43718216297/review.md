<!-- autose -->
# Independent review: PR #8, round 1

**Verdict: ❌ REQUEST CHANGES** → route: `implement`

Reviewer: claude-opus-5-5 in a separate job, contents:read token, saw only the issue, the diff and the repository at the PR head.

Request changes. The new `limit` argument works on a fresh table but breaks the query cache in both directions. A limited search stores its truncated result under the plain query key, so a later `db.search(q)` with no limit returns too few documents. And a cache hit returns before `limit` is applied, so the limit is ignored for a query that was searched before. The full suite passes (230 passed) because the new tests never repeat a query; my probe confirmed both bugs. The approach is fine; the code needs fixing: cache only complete results, slice cached results by `limit`, check for negative limits, and add tests that mix limited and unlimited searches.

## Requirements from the issue (reviewer's reading)

| Requirement | Met | Evidence |
|---|---|---|
| search(cond, limit=N) returns at most N matches | partly | On a fresh table, probe gives limit=2 -> [1, 3]. But after an earlier unlimited search with the same query, limit=1 returns [1, 3, 4] because the cache hit at tinydb/table.py:266-268 returns before limit is applied. |
| Same order as today's search() | yes | Iterates _read_table().items() in the same order as before (table.py:274). Probe gives [1, 3] for limit=2. |
| Without limit behaves exactly as now | no | Probe: after db.search(q, limit=1), db.search(q) returns [1] instead of [1, 3, 4]. The truncated list is stored under the cache key `cond` at table.py:297. |
| Stops early instead of building the full list | yes | The loop breaks once len(docs) >= limit (table.py:275-276). |
| Existing behaviour and query cache correctness preserved | no | Cache poisoning shown by the probe in both directions (limited then unlimited, and unlimited then limited). The full suite passes (230 passed) only because no test mixes the two. |
| C1–C5 hold | yes | The diff only touches Table.search. There are no storage writes, import changes or new dependencies (ARCHITECTURE.md:112-116). Optional is already imported, since the module loads and the tests pass. |
| Tests cover new behaviour including cache interaction | no | tests/test_search_limit.py has only two tests, each on a fresh DB with one search call. Nothing covers repeated searches, limit=0 or negative values. |

## Findings

| Severity | Category | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|---|
| blocker | code | `tinydb/table.py:297` | A limited search stores its truncated result in the query cache under the plain `cond` key. Every later search with the same query, even one without a limit, gets the truncated list. That silently returns wrong (missing) results and breaks the requirement that search() without limit behaves exactly as before. | Probe: db.search(q, limit=1); db.search(q) -> [1], expected [1, 3, 4]. | Cache only complete results: write to the cache only when limit is None, or when the loop ran to the end without hitting the limit. Alternatively, compute or cache the full result and slice. |
| major | code | `tinydb/table.py:268` | On a cache hit the method returns the cached list before `limit` is considered, so limit is ignored whenever the query was searched before. | Probe: db.search(q); db.search(q, limit=1) -> [1, 3, 4], expected [1]. | Apply the limit on the cache-hit path: `return cached_results[:limit]` when limit is not None. |
| major | tests | `tests/test_search_limit.py:1` | The tests never exercise the query cache together with limit (repeated searches with and without limit), so both cache bugs pass the suite. | Full suite: 230 passed, while the probe shows wrong results. | Add tests for: a limited search followed by an unlimited search with the same query, an unlimited search followed by a limited one, limit=0, and limit larger than the number of matches. |
| minor | code | `tinydb/table.py:275` | A negative limit silently returns []. That is surprising and differs from slicing semantics. Invalid values should probably raise ValueError, or at least be documented. | Probe: search(q, limit=-1) -> []. | Validate the argument: raise ValueError if limit is not None and limit < 0. |

## Commands the reviewer actually ran

- `python -m pytest -q`
- `python /home/runner/work/_temp/autose/review-scratch/probe_limit.py`

## Risks considered

- Query cache interaction between limited and unlimited calls (confirmed broken)
- Ordering of results relative to the existing search() (ok)
- Edge values limit=0, negative, and larger than the number of matches
- Forwarding through TinyDB.__getattr__ to the default table (works)
- Uncacheable queries (is_cacheable False) are not affected by the caching bug
- ARCHITECTURE constraints C1–C5 (not violated)
- Type annotations and mypy compatibility (Optional[int] is fine)

<sub>cost $0.116, 8 turns</sub>
