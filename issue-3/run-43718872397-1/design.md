# design.md

Add an optional keyword `limit` to Table.search. The full result is always computed and cached unchanged. The limit is applied only to the returned fresh list copy. TinyDB.search needs no change because __getattr__ forwards it.

## Approach

In `Table.search(self, cond, limit=None)`: (1) validate `limit` up front using the provisional ASM-001 behaviour. None means no limit; a non-int (including bool) raises TypeError; a negative value raises ValueError; 0 returns []. (2) On a cache hit, return `cached_results[:limit]`; a slice with `None` is a full copy, so unlimited behaviour is identical to today. (3) On a miss, build the full `docs` list exactly as today and cache `docs[:]` (the full list, so a later unlimited search is complete, FR-SRCH-004). Then return `docs[:limit]`. The order is the table's stored order, so a limited result is a prefix of the unlimited result (FR-SRCH-002). Unlimited calls still return a fresh list each time (FR-SRCH-003). A limit >= the match count returns everything (FR-SRCH-005). `TinyDB.search` is forwarded by `TinyDB.__getattr__` to the default table, which passes through both positional and keyword args (FR-SRCH-006). Early termination (FR-SRCH-008, ASM-003) is not implemented, as the spec marks it NEEDS-CLARIFICATION with default (b). The docstring is updated to document `limit`.

## Files and symbols to change

| File | Change | Symbol | Kind | Symbol change | What |
|---|---|---|---|---|---|
| `tinydb/table.py` | modify | `Table.search` | method | modify | New signature `search(self, cond, limit: Optional[int] = None)`. Validate `limit`. Return `cached_results[:limit]` on a cache hit and `docs[:limit]` on a miss. Always cache the full `docs[:]`. Update the docstring. |

## Acceptance criteria → code → test

| AC | Symbols | Test idea |
|---|---|---|
| FR-SRCH-001.AC-1 | Table.search | Five docs n=1..5 in a MemoryStorage table; search(Query().n >= 1, limit=2) has length 2. |
| FR-SRCH-001.AC-2 | Table.search | Call search(cond) first to fill the cache, then search(cond, limit=2) == [{'n':1},{'n':2}]. |
| FR-SRCH-001.AC-3 | Table.search | With a fresh cond, search(cond, limit=1) gives one doc with doc_id 1 and content {'n':1}. |
| FR-SRCH-002.AC-1 | Table.search | search(cond, limit=3) returns doc_ids [1,2,3] and contents [{'n':1},{'n':2},{'n':3}]. |
| FR-SRCH-002.AC-2 | Table.search | Build two identical tables; compare search(cond, limit=3) on the first with search(cond)[:3] on the second, checking doc_id as well. |
| FR-SRCH-003.AC-1 | Table.search | search(Query().n >= 3) with no limit returns three Document objects with doc_ids [3,4,5] and the expected contents. |
| FR-SRCH-003.AC-2 | Table.search | Call search(cond) twice; both results hold all five docs and `r1 is not r2`. |
| FR-SRCH-004.AC-1 | Table.search | On a fresh cond, call search(cond, limit=2) then search(cond); the second returns doc_ids [1..5]. |
| FR-SRCH-005.AC-1 | Table.search | With cond n <= 3 and limit=10, the result has doc_ids [1,2,3]. |
| FR-SRCH-005.AC-2 | Table.search | With cond n <= 3 and limit=3, the result has doc_ids [1,2,3]. |
| FR-SRCH-006.AC-1 | Table.search | db = TinyDB(storage=MemoryStorage) with five error docs; db.search(Query().level == 'error', limit=2) returns the first two docs in order (forwarded via TinyDB.__getattr__). |
| FR-SRCH-006.AC-2 | Table.search | db.search(Query().level == 'error') with no limit returns all five docs in insertion order. |

## Architecture constraints (ARCHITECTURE.md)

- C1: No storage changes.
- C2: No new query operation. The cache key is still the unchanged query hash and `limit` is not part of it, because the cache always stores the full result.
- C3: search is read-only. No writes happen outside `_update_table` and cache invalidation is untouched.
- C4: Only table.py is edited and no new imports are added beyond typing names already in use (Optional). Layering is unchanged.
- C5: Standard library only. Only slicing and isinstance checks are used.

## Alternatives considered

- Early termination: stop iterating once `limit` matches are found: Spec ASM-003/Q-003 default says it is not required. A partial result must not be cached, so a limited miss would not populate the cache, which adds a second code path and changes cache side effects. Keep the change small.
- Cache the limited result under a key that includes limit (e.g. wrapper or tuple key): The cache key is the query itself (ADR-3). A composite key changes the cache design, which is out of scope, and would not serve unlimited lookups from a limited entry.
- Add an explicit `search` method to TinyDB: Unnecessary: __getattr__ already forwards args and kwargs to the default table.
- Python slice semantics for negative limit, with no validation: Silently returns surprising results (e.g. limit=-1 drops the last match). ASM-001 default is to raise on negative or non-int values.
- Use itertools.islice on the cached list: A plain slice is simpler and the standard library is not needed.

## Risks

- FR-SRCH-007 (limit of 0, negative, None or non-int) and FR-SRCH-008 (early termination) are NEEDS-CLARIFICATION in the spec. The design follows the provisional ASM-001 (0 returns [], None means no limit, negative raises ValueError, non-int or bool raises TypeError) and ASM-003 (no early termination). If the spec owner chooses differently, only the validation lines change, or a second code path is needed for early termination.
- Because the full result is always computed and cached, `search(cond, limit=N)` is no faster than `search(cond)[:N]`. The issue's performance motivation is not met, by design (ASM-003).
- Cached Document objects are shared between the cache and returned lists. The existing docstring caveat applies unchanged to limited results.
- Validation order: it must run before the cache lookup so invalid limits always raise, even on a cache hit. The tester should be aware that bool is a subclass of int and is rejected only if the implementation checks for it explicitly.
- Spec FR-SRCH-002.AC-1 and TERM-2 assume stored order equals ascending doc_id. This holds for the fixtures used, but a table with non-ascending storage order would return stored order, which is the same as today.

## Stage check: PASSED

