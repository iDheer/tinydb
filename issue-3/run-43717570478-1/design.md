# design.md

Add an optional keyword-only `limit` parameter to `Table.search()` (reached by `TinyDB.search` via `__getattr__`, so no change to database.py). The scan stops after N matches, the result is the first N in table order, and a truncated result is never written to the query cache.

## Approach

Only `Table.search` in tinydb/table.py changes.

1. Signature: `search(self, cond, *, limit: Optional[int] = None)`. I made it keyword-only because the spec only defines the `limit=N` form (Q-006) and this leaves positional use free to define later. The `Optional` import is already present in table.py.

2. Validation, before any work (ASM-002 and ASM-003, both provisional):
   - `None` means no limit.
   - A non-int raises `TypeError`. `bool` is rejected too, because it subclasses `int`.
   - A negative value raises `ValueError`.
   - `0` returns `[]` immediately, without scanning or touching the cache.

3. Cache hit: the existing code returns `cached_results[:]`. With a limit it returns `cached_results[:limit]`. The cache always holds the full result, so this is correct for AC-5 and for order (FR-SEARCH-002).

4. Cache miss, no limit: behaviour and caching stay exactly as today, so existing tests are unaffected (FR-SEARCH-003).

5. Cache miss, with a limit:
   - Iterate `self._read_table().items()` in the same order as today.
   - Append `document_class(doc, document_id_class(doc_id))` for each doc where `cond(doc)` is true.
   - Break as soon as `len(docs) == limit`. This gives early termination (GOAL-001, Q-003) without changing order.
   - Keep a `truncated` flag that is set when the loop breaks early.

6. Caching rule: write to `self._query_cache[cond]` only if the query is cacheable and the scan was not truncated. A scan that ran to the end saw every match, so the full result is known and safe to cache. A truncated result is never cached, so a later unlimited `search(cond)` still returns every match (RSK-001, FR-SEARCH-004). If the limit is hit on the last document, the code treats the result as truncated and does not cache it. That costs one extra scan later and is always correct.

7. Return a fresh list. Update the docstring to describe `limit`, the validation behaviour, and the fact that limited results are not cached.

For the unlimited path, either keep the list comprehension or use one loop with an optional break. I would use a single loop, with `limit is None` meaning no break, to avoid duplicated construction code.

## Files and symbols to change

| File | Change | Symbol | Kind | Symbol change | What |
|---|---|---|---|---|---|
| `tinydb/table.py` | modify | `Table.search` | method | modify | New `*, limit: Optional[int] = None` parameter. Validates `limit` (`None` means no limit, `0` returns `[]`, negatives raise `ValueError`, non-int and bool raise `TypeError`). On a cache hit it returns `cached_results[:limit]`. On a miss it scans in table order and stops after `limit` matches. It caches the result only if the query is cacheable and the scan was not truncated. Docstring updated. |

## Acceptance criteria → code → test

| AC | Symbols | Test idea |
|---|---|---|
| FR-SEARCH-001.AC-1 | Table.search | Insert 25 docs (15 with level=='error'), call search(Query().level=='error', limit=10), and assert len == 10 and every doc has level == 'error'. |
| FR-SEARCH-001.AC-2 | Table.search | With 3 matching docs, search(q, limit=10) returns exactly those 3 docs. |
| FR-SEARCH-001.AC-3 | Table.search | With exactly 10 matching docs, search(q, limit=10) has length 10 and equals the unlimited result. |
| FR-SEARCH-001.AC-4 | Table.search | Use a TinyDB with MemoryStorage and 15 inserted matching docs. Assert db.search(q, limit=10) has length 10 and does not raise (forwarded via __getattr__). |
| FR-SEARCH-001.AC-5 | Table.search | Call search(q) to fill the cache, then search(q, limit=10) with the same query object. Assert length 10 and that the result equals the first 10 of the unlimited result. |
| FR-SEARCH-002.AC-1 | Table.search | Insert n=1 error, n=2 info, n=3 error, n=4 error. Assert search(q, limit=2) equals search(q)[:2], i.e. n == [1, 3]. |
| FR-SEARCH-002.AC-2 | Table.search | With 12 matches, assert [d.doc_id for d in search(q, limit=5)] equals the first 5 doc_ids of the unlimited search. Run it on both a cold and a warm cache. |
| FR-SEARCH-003.AC-1 | Table.search | With 15 matches, search(q) returns 15 docs in insertion order. |
| FR-SEARCH-003.AC-2 | Table.search | Call search(q) twice and assert equal results. Pop an item from the first result list and assert a third call still returns the full length (a fresh list each time). |
| FR-SEARCH-003.AC-3 | Table.search | search with a query that matches nothing returns []. |
| FR-SEARCH-003.AC-4 | Table.search | Run the existing tests (tests/test_tinydb.py and others) unchanged and assert they all pass. This is a regression run and needs no new test. |

## Architecture constraints (ARCHITECTURE.md)

- C1: Storages are not touched. `search` still uses only `_read_table()`, which goes through `storage.read()`.
- C2: No new query operation and no change to query hashes. `limit` is deliberately not part of the cache key, so truncated results are never cached under `cond`. Only full results are stored, which keeps the hash contract intact.
- C3: `search` is read-only and writes nothing to storage. Cache invalidation after writes still goes through `_update_table`, unchanged. The limited-search path only skips cache writes.
- C4: No new imports and no change to module layering. Only table.py changes.
- C5: Plain Python only. No new dependency, and `Optional` is already imported from typing.

## Alternatives considered

- Always compute the full result, cache it, then slice to `limit`: Simple and cache-safe, but it ignores the stated motivation that building the full list every time is costly. The first limited call would still scan the whole table.
- Cache the truncated result under a key that includes the limit, e.g. (cond, limit): The cache is keyed by the query object and `LRUCache` has capacity 10, so extra keys would evict useful entries. It would also need a hashable wrapper and would touch the cache design (ADR-3), which is out of scope.
- Cache the truncated list under `cond`: This corrupts later unlimited searches (RSK-001), which is exactly the bug the spec warns about.
- Add `limit` to `TinyDB.search` explicitly, or to `all()`/`count()`/`get()`: `TinyDB.__getattr__` already forwards `search` unchanged (DEP-001). Other methods are out of scope (Q-005).
- Make `limit` positional-or-keyword: Positional use is unspecified (Q-006). Keyword-only is the smaller API commitment and is easy to loosen later.
- Treat `limit=0` or a negative `limit` as no limit, or use Python slice semantics: These would silently return many results for an apparent 'zero'. Returning `[]` for 0 and raising `ValueError` for negatives is the provisional default (ASM-002).

## Risks

- The spec marks the edge-case semantics as provisional: limit=0 returns [] (Q-001), a negative limit raises ValueError (Q-001), None means no limit, and a non-int raises TypeError (Q-002). The maintainer may choose differently. The tester should treat these as provisional behaviour.
- FR-SEARCH-004 (a limited search must not change a later unlimited search) is only a candidate requirement in the spec, but the design implements it anyway because RSK-001 has high impact. The tester can add tests for it safely.
- Early termination (Q-003) is treated as a SHOULD goal. It is hard to assert beyond counting calls to a custom query callable, and a test that relies on it is only valid if the maintainer confirms it.
- Cache hit on a limited search returns the cache's shared Document objects, with the same read-only caveat already in the docstring.
- If the limit is reached on the very last matching document, the result is not cached, because the code cannot tell the scan was complete without reading further. This costs a repeat scan later but is never incorrect.
- Keyword-only `limit` means `search(q, 10)` raises TypeError. This is consistent with the spec, which only specifies the keyword form (Q-006), but a positional call would surprise some users.
- The issue text contained no instructions aimed at the agent.

## Stage check: PASSED

