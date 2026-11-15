<!-- autose -->
# Independent review: PR #8, round 1

**Verdict: ❌ REQUEST CHANGES** → route: `implement`

Reviewer: claude-opus-5-5 in a separate job, contents:read token, saw only the issue, the diff and the repository at the PR head.

The PR adds `limit` to Table.search and stops the scan early. Order is kept and the existing 230 tests pass. However, it ignores the query cache in both directions. (1) A truncated result is cached under the query, so a later unlimited `search(q)` returns only the limited subset; the probe got 3 instead of 15, which is silent data loss in results. (2) A cache hit returns the full list and ignores `limit`; the probe got 15 instead of 10. The new tests never run two searches on the same query, so they miss both bugs. The design (cache only complete scans, slice on cache hit, validate limit, keyword-only) is sound, but the code does not follow it, so the PR goes back to implementation.

## Requirements from the issue (reviewer's reading)

| Requirement | Met | Evidence |
|---|---|---|
| search(cond, limit=N) returns at most N matching documents | partly | Cold cache: probe 'limited first: 3' is correct. Warm cache: probe 'limited after cache (expect 10): 15'. At table.py:266-268 a cache hit returns cached_results[:] and ignores limit. |
| Same order as unlimited search (first N) | yes | Probe 'order: [0, 1, 2]'. tests/test_search_limit.py::test_search_limit_returns_first_matches passes ([1, 3]). |
| Without limit, behaves exactly as before | no | Probe 'unlimited after limited (expect 15): 3'. table.py:295-297 caches the truncated docs list under cond, so a later search(q) returns only 3 documents. search(q, limit=0) also caches [] under q. |
| Limited search does not corrupt the cache, and a warm-cache limited search honours limit | no | Same probe results as above: the truncated list is cached at table.py:297, and the cache-hit path at table.py:268 ignores limit. |
| Early termination of the scan | yes | Probe: the condition was called 2 times with limit=2 on a 16-document table. Loop break at table.py:275-276. |
| Edge values handled sensibly | partly | Probe: limit=0 gives 0 and limit=-1 silently gives 0. There is no validation, and both results are cached as [] under the query. |
| Existing suite passes; C1-C5 hold | partly | python -m pytest -q: 230 passed. C1, C2, C4 and C5 are untouched. C3 says the query cache must reflect the data; it is cleared only on writes, so caching a truncated result leaves the cache wrong until the next write. |

## Findings

| Severity | Category | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|---|
| blocker | code | `tinydb/table.py:297` | A truncated result from a limited search is written to the query cache under `cond`. Every later unlimited `search(cond)` on the same table then returns only the truncated subset until the next write. This silently drops results, which breaks 'without limit it should behave exactly as it does now'. The PR description claims the result is 'cached exactly like before', and that is the bug. It also contradicts design.md step 6. | Probe: db.search(q, limit=3) and then db.search(q) gives 3 instead of 15. | Cache only when the scan ran to completion: when limit is None, or when the loop never broke early. Track a `truncated` flag and skip the cache write when it is set. |
| major | code | `tinydb/table.py:268` | On a cache hit the limit is ignored and the full cached list is returned. Any limited search that follows an unlimited search with the same query returns more than `limit` documents. | Probe: db.search(q) and then db.search(q, limit=10) gives 15 documents. | Return `cached_results[:limit]` when limit is not None, otherwise `cached_results[:]`. |
| major | tests | `tests/test_search_limit.py:1` | The tests only cover a cold-cache limited search and a plain unlimited search. Nothing covers the cache interaction (limited then unlimited, or unlimited then limited), and that is where both bugs are. | The file has 2 tests and neither runs two searches with the same query. | Add tests for: limited then unlimited returns all matches; unlimited then limited honours the limit; limited search after an insert; limit=0; limit greater than the number of matches; db.search forwarding; and an early-termination call count. |
| minor | code | `tinydb/table.py:249` | `limit` is not validated, and it is positional-or-keyword, while the design specified keyword-only. Negative values silently return [] (and the [] gets cached). Non-int values such as '10' raise an obscure TypeError from the comparison inside the loop. The design called for ValueError on negatives, TypeError on non-int/bool, and an early return of [] for 0 without touching the cache. | Probe: limit=-1 gives 0 with no error. | Make the signature `search(self, cond, *, limit=None)`. Validate limit up front, and return [] for limit=0 before the cache is involved. |

## Commands the reviewer actually ran

- `python -m pytest -q`
- `python /home/runner/work/_temp/autose/review-scratch/probe_limit.py`

## Risks considered

- Query cache poisoning by truncated results (confirmed)
- Cache hit ignoring limit (confirmed)
- Order preservation on cold and warm cache
- Edge values: 0, negative, None, non-int
- Early termination versus full scan
- TinyDB.search forwarding via __getattr__
- Shared cached Document objects returned by limited searches
- Non-cacheable queries (is_cacheable False), which go through the uncached path and are fine
- ARCHITECTURE.md C1-C5 compliance
- No instructions aimed at the agent found in the issue text

<sub>cost $0.176, 8 turns</sub>
