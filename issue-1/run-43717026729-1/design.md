# design.md

Include the query path (self._path) in the hash value built by Query.fragment() so fragment queries on different paths no longer compare equal or share a Table query-cache entry.

## Approach

In tinydb/queries.py, change the hash tuple in Query.fragment from ('fragment', freeze(document)) to ('fragment', self._path, freeze(document)), the same shape one_of uses ('one_of', self._path, freeze(items)). This is a one-line change. _generate_test already substitutes None when the query is not cacheable (path contains a callable from map()), and self._path is a tuple of str/callables, so it is hashable like in one_of. An empty path (allow_empty_path=True, e.g. Query().fragment(...)) gives (), which is still valid and distinct from non-empty paths. Fixing the hash fixes both the cache collision (FR-QRY-001) and equality (FR-QRY-002), since QueryInstance.__eq__ compares _hash.

## Files and symbols to change

| File | Change | Symbol | Kind | Symbol change | What |
|---|---|---|---|---|---|
| `tinydb/queries.py` | modify | `Query.fragment` | method | modify | Change hashval passed to _generate_test to ('fragment', self._path, freeze(document)); the test logic and allow_empty_path=True stay unchanged. |

## Acceptance criteria → code → test

| AC | Symbols | Test idea |
|---|---|---|
| FR-QRY-001.AC-1 | Query.fragment | MemoryStorage db with A and B; search home.fragment({'city':'Pune'}) then work.fragment(same); assert the second result == [B] and A is not in it. |
| FR-QRY-001.AC-2 | Query.fragment | Fresh db with A and B; first search User.home.fragment({'city':'Pune'}) returns exactly [A]. |
| FR-QRY-001.AC-3 | Query.fragment | Search work.fragment first (gives [B]), then home.fragment; assert the result == [A] and B is not in it. |
| FR-QRY-001.AC-4 | Query.fragment | Run home, then work, then home again on the same db; assert the final result == [A]. |
| FR-QRY-002.AC-1 | Query.fragment | Assert (User.home.fragment({'city':'Pune'}) == User.work.fragment({'city':'Pune'})) is False. |
| FR-QRY-002.AC-2 | Query.fragment | Assert User.home.fragment({'city':'Pune'}) == User.home.fragment({'city':'Pune'}) is True, and that the two hashes are equal. |

## Architecture constraints (ARCHITECTURE.md)

- C2: The fragment hash now holds the operation tag, the path and the frozen argument, as C2 requires. It is still built via _generate_test, which sets it to None when the query is not cacheable.
- C4: Only queries.py changes. It still imports only utils (freeze) and gains no new imports.
- C5: No new dependencies; the change uses only existing code.
- C3: Table and _update_table are untouched; cache invalidation on writes is unchanged.

## Alternatives considered

- Disable or clear the query cache (or key it differently in Table.search): Out of scope per the spec, and it breaks ADR-3, which says the query's hash must carry its full meaning. The bug is in the hash, not the cache.
- Audit and fix all Query methods that take a path: ASM-002/Q-002 limit the scope to fragment(). Other methods such as one_of already include self._path.
- Change _generate_test to inject self._path into every hashval automatically: A larger refactor that would alter hashes of every existing query. It is not needed for this bug.

## Risks

- The spec's FR-QRY-002 is only an ASSUMPTION-ONLY candidate (priority UNSET), but the fix satisfies it anyway, so there is no conflict.
- Hash tuples change shape for fragment queries, so any code or test that compares against the literal tuple ('fragment', frozen) would break. A grep found none in the source files read, but the existing tests were not checked.
- Other path-based queries (e.g. matches, search, test, any/all) were not audited, per Q-002. Query.test builds its hash from the function and arguments, and the remaining methods were not inspected for a similar missing path.

## Stage check: PASSED

