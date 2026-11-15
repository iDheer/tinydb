<!-- autose -->
# Independent review: PR #10, round 1

**Verdict: ❌ REQUEST CHANGES** → route: `implement`

Reviewer: claude-opus-5-5 in a separate job, contents:read token, saw only the issue, the diff and the repository at the PR head.

I'm requesting changes on PR #10. The approach is sound, but invalid limits give results that depend on whether the query cache is warm.

**What works:**
- Matches come back in the original order, capped at the limit.
- The scan stops early once the limit is reached.
- Limited searches never put partial results into the cache.
- Searching without a limit behaves exactly as before.
- All 230 tests pass and mypy reports no issues.

**The problem (major, code):** the cached path uses Python slicing and the uncached path uses a counting loop, and the two disagree for invalid limits:
- With `limit=-1`, a cold cache returns `[]`, but a warm cache returns every match except the last one (9 of 10 in my probe).
- With `limit=2.0`, a cold cache works, but a warm cache raises `TypeError`.

The same call should never change its answer depending on cache state. The fix is to accept only `None` or a non-negative int at the top of `search()` and reject anything else.

**Smaller issues:** the tests don't cover `limit=0`, a limit larger than the number of matches, invalid limits, or the early stop. The signature line is too long, and the docstring doesn't mention these cases.

## Requirements from the issue (reviewer's reading)

| Requirement | Met | Evidence |
|---|---|---|
| At most N matching documents returned | yes | Probe: cold limit=3 -> [1, 4, 7]; limit=1000 returns all 10 matches; limit=0 -> [] both cold and warm. tests/test_search_limit.py passes. |
| Same order as unlimited search (first N) | yes | Probe: full=[1,4,7,...,28], cold limit=3 == warm limit=3 == full[:3] -> True |
| Without limit, behaviour unchanged | yes | tinydb/table.py:280-308 unchanged path when limit is None; probe 'none True'; full suite 230 passed |
| Result independent of cache state; no partial result cached | partly | Partial results are not cached (table.py:270-278 returns before caching; probe 'after limited, full: True'). But for limit=-1 a cold cache returns [] and a warm cache returns 9 of 10 docs (probe 'neg cold [] neg warm [1, ..., 25] consistent False'). limit=2.0 works cold but raises TypeError warm. |
| Early stop | yes | Probe: with limit=2 and matches at docs 1 and 4, cond was called 4 times out of 30 docs |
| Works via TinyDB and Table | yes | Probe: db.search(q, limit=...) and db.table('_default').search(q, limit=2) -> [1, 4] |
| Existing tests pass; C1-C5 hold | yes | python -m pytest -q: 230 passed; python -m mypy tinydb: no issues; diff only touches Table.search (read-only, no storage writes, no new imports) |

## Findings

| Severity | Category | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|---|
| major | code | `tinydb/table.py:268` | The same call can give different results depending on whether the query cache is warm. The cached path uses Python slicing (`cached_results[:limit]`) and the uncached path uses a counting loop (`len(docs) >= limit`). These disagree for negative limits. With limit=-1, a cold search returns [] but a warm search returns every match except the last. Asking for 'at most -1' documents and getting 9 back is wrong. The cache is supposed to be invisible, and ADR-3 says search correctness must not depend on it. Non-int limits also split: limit=2.0 works cold and raises TypeError warm. | Probe output: `neg cold [] neg warm [1, 4, 7, 10, 13, 16, 19, 22, 25] consistent False`; `float [..2 docs..]` vs `float warm exc TypeError slice indices must be integers...` | Check `limit` at the start of search(): accept only None or a non-negative int (reject bool if you like), and raise ValueError/TypeError for anything else. Then both paths agree. Add tests for limit=0 and for rejecting a negative limit on both a cold and a warm cache. |
| minor | tests | `tests/test_search_limit.py:1` | The tests do not cover limit=0, a limit larger than the number of matches, invalid limits, the early stop itself (that cond stops being called), or a limited search on a cold cache followed by a limited search on a warm cache with the same query. | The file has only two tests: a cold limit=2 search, and a limit=1 then full then limit=2 sequence. | Add parametrized tests for limit in {0, larger than the match count} on both cold and warm cache. Add a test that counts cond calls to show the early stop. Add a test for rejecting a negative limit. |
| nit | code | `tinydb/table.py:249` | The signature line is longer than the file's usual line width. The docstring says nothing about limit=0, negative values, or the fact that limited searches skip the cache. | `def search(self, cond: QueryLike, limit: Optional[int] = None) -> list[Document]:` | Wrap the signature. In the docstring, say that limit must be None or >= 0 and that a limited search is not cached. |

## Commands the reviewer actually ran

- `python -m pytest -q`
- `python /home/runner/work/_temp/autose/review-scratch/probe_limit.py`
- `python -m mypy tinydb`

## Risks considered

- A truncated result stored in the query cache and returned by later full searches: checked, it does not happen
- The cached list being changed through the returned slice: checked, a slice is a copy
- Order differing between cached and uncached paths: checked, it is the same
- Results depending on cache state for edge-case limits (negative, non-int): found inconsistent
- Non-cacheable queries (is_cacheable False) with a limit: the limited path skips the cache anyway, so no issue
- The TinyDB __getattr__ forwarding passing the keyword through: checked, it works
- Breaking C3/C4/C5: the change is read-only, adds no imports and no storage writes
- Calling cond on documents after the limit is reached (side-effecting test functions): the loop breaks before calling cond again

<sub>cost $0.197, 10 turns</sub>
