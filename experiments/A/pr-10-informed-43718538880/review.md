<!-- autose -->
# Independent review: PR #10, round 1

**Verdict: ❌ REQUEST CHANGES** → route: `implement`

Reviewer: claude-opus-5-5 in a separate job, contents:read token, saw only the issue, the diff and the repository at the PR head.

The core feature works: limited results are correct in count and order, the scan stops early, the cache is never poisoned, and all 230 tests pass. However, `limit` is not validated, so the same call returns different results depending on the hidden cache state. limit=-1 returns [] on a cold cache but all matches except the last on a warm one, and a float limit returns docs on a cold cache but raises TypeError on a warm one. The design called for validation and the implementation left it out. The fix is small: validate before the cache lookup and add edge-case tests. Routing to implement.

## Requirements from the issue (reviewer's reading)

| Requirement | Met | Evidence |
|---|---|---|
| R1: at most N results | yes | Probe: 'limit=10 cold 10', 'limit=10 warm 10', 'limit=100 15', 'table limit 4'. tests/test_search_limit.py passes. |
| R2: same order as unlimited search | yes | Probe: doc_ids of limit=10 equal full[:10] on both a cold and a warm cache (True/True). test_search_limit_returns_first_matches_in_order gives [1, 3]. |
| R3: unchanged behaviour without limit | yes | The unlimited path at tinydb/table.py:283-308 is unchanged, and the cache hit uses cached_results[:None], which is a full copy. Full suite: 230 passed. |
| R4: limited search does not poison the cache | yes | tinydb/table.py:270-278 returns without writing to the cache. Probe: 'full after limited 15', 'after insert 16', 'after clear full 15'. |
| R5: early stop | yes | Probe: a custom cond called with limit=2 was evaluated only on docs [0, 1]. |
| R6: consistent result regardless of cache state; defined behaviour for odd limits | no | Probe: 'limit=-1 cold len 0 warm len 14'. Also 'float limit cold 3' but 'float warm raises TypeError'. No validation exists (table.py:266-278). |
| R7: existing tests pass; C1-C5 hold | yes | python -m pytest -q: 230 passed. The diff touches only Table.search and adds no imports, storage writes or query-hash changes. |

## Findings

| Severity | Category | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|---|
| major | code | `tinydb/table.py:268` | For the same input, the result depends on the hidden query-cache state. With a negative limit, a cold cache returns [] (the loop breaks at once because len(docs) >= -1), while a warm cache returns cached_results[:-1], which is every match except the last. With a float limit, a cold cache returns ceil(limit) docs, while a warm cache raises TypeError from slicing. A caller computing something like `limit=n-1` can silently get completely different results depending on whether the same query ran before. The design promised validation (TypeError for non-int or bool, ValueError for negatives), but the implementation has none. | Probe output: 'limit=-1 cold len 0 warm len 14'; 'float limit cold 3'; 'float warm raises TypeError slice indices must be integers...' | Validate limit at the top of search(), before the cache lookup: None means no limit; reject bool and non-int with TypeError; reject negative values with ValueError; return [] for 0. Then both paths agree. |
| minor | tests | `tests/test_search_limit.py:1` | The tests cover only the basic order and cache-interaction cases. Nothing covers limit greater than the match count, limit equal to the match count, limit=0, invalid or negative limits, early termination (a call-counting cond), or a write after a limited search. Those gaps let the cold/warm inconsistency above go unnoticed. | The file has 2 tests (20 lines). The spec ACs FR-SEARCH-001.AC-2/AC-3 and the edge cases Q-001/Q-002 have no tests. | Add tests for limit > matches, limit == matches, limit=0, negative and non-int limits (same behaviour on cold and warm cache), early stop via a counting callable, and insert-after-limited-search. |
| nit | code | `tinydb/table.py:249` | limit is positional-or-keyword, although the design said keyword-only. Positional use (search(q, 3)) works. That is acceptable, but it differs from the design and becomes a public API commitment. | Probe: 'positional 3'. The signature is `search(self, cond, limit=None)`. | Either make it keyword-only (`*, limit=None`) as designed, or document the positional form deliberately. |
| nit | code | `tinydb/table.py:274` | The limit check sits at the top of the loop, so the scan reads one more element before breaking, and a limited scan that runs to the end is not cached even though it saw every match. This is correct but slightly wasteful. | table.py:273-278 | Break right after the append when len(docs) == limit. Optionally cache the result when the loop completes without truncation. |

## Commands the reviewer actually ran

- `python -m pytest -q`
- `python /home/runner/work/_temp/autose/review-scratch/probe_limit.py`

## Risks considered

- Cache poisoning by truncated results: checked, not present
- Order divergence between cached and uncached paths: checked, consistent
- Edge-case limit values (0, negative, float, bool) behaving differently across cache states: present
- Shared Document objects returned from the cache by a limited search: same caveat as before, documented
- TinyDB.__getattr__ forwarding the new argument: works
- Cache invalidation after a write following a limited search: works
- C1-C5 architecture constraints: unaffected
- Untrusted issue text: contains no instructions aimed at agents

<sub>cost $0.192, 8 turns</sub>
