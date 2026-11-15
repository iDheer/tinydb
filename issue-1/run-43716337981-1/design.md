# design.md

Add the query path to the hash of Query.fragment() so fragment queries on different paths no longer share a hash, compare equal, or collide in the Table query cache. This is a one-line change in tinydb/queries.py.

## Approach

Query.fragment() builds its hash as ('fragment', freeze(document)) and leaves out self._path. Every sibling method (exists, matches, search, test, any, all, one_of) uses (tag, self._path, ...). QueryInstance equality and hashing use the hash value, and Table.search uses the query as its LRUCache key. So User.home.fragment(x) and User.work.fragment(x) are treated as the same query, and the second search gets the first one's cached result. The fix changes the hash to ('fragment', self._path, freeze(document)). This matches the other methods and constraint C2. Path resolution in _generate_test is unchanged. Root-level Query().fragment({...}) has an empty path (), which is hashable, so it keeps working. A path that contains a callable (from map()) still makes is_cacheable() return False, and _generate_test then sets the hash to None, as before. The change fixes AC-1 to AC-3 of FR-QFRAG-001 and also the candidate FR-QFRAG-002 (unequal queries on different paths, equal queries on the same path), since both depend on the hash.

## Files and symbols to change

| File | Change | Symbol | Kind | Symbol change | What |
|---|---|---|---|---|---|
| `tinydb/queries.py` | modify | `Query.fragment` | method | modify | Change the hash passed to _generate_test from ('fragment', freeze(document)) to ('fragment', self._path, freeze(document)). Keep allow_empty_path=True and the test logic unchanged. |

## Acceptance criteria → code → test

| AC | Symbols | Test idea |
|---|---|---|
| FR-QFRAG-001.AC-1 | Query.fragment, Query._generate_test | Use TinyDB(storage=MemoryStorage) with the ana and raj documents. Run db.search(User.home.fragment({'city':'Pune'})), then db.search(User.work.fragment({'city':'Pune'})) on the same instance. Assert the second result is a list with only the document named 'raj'. |
| FR-QFRAG-001.AC-2 | Query.fragment | On a fresh TinyDB(MemoryStorage) with the two documents, run only db.search(User.work.fragment({'city':'Pune'})). Assert the result contains only 'raj'. |
| FR-QFRAG-001.AC-3 | Query.fragment | On the same instance, run the work search first, then db.search(User.home.fragment({'city':'Pune'})). Assert the second result contains only 'ana'. |
| FR-QFRAG-002.AC-1 | Query.fragment, QueryInstance.__eq__, QueryInstance.__hash__ | Assert User.home.fragment({'city':'Pune'}) == User.work.fragment({'city':'Pune'}) is False, and that their hash() values differ. |
| FR-QFRAG-002.AC-2 | Query.fragment, QueryInstance.__eq__, QueryInstance.__hash__ | Assert User.home.fragment({'city':'Pune'}) == User.home.fragment({'city':'Pune'}) is True and that their hashes are equal. |

## Architecture constraints (ARCHITECTURE.md)

- C2: The fragment hash now holds the operation tag, the path and the frozen argument, as C2 requires. Hash None is still used for non-cacheable queries (map() paths) through _generate_test. The path is still resolved by _generate_test.
- C4: queries.py keeps importing only utils, and no new imports are added. Table, database and storages are not touched.
- C5: No new dependency is added. The change uses only tuple composition with existing names.
- C3: Table and _update_table are not changed, so the cache is still cleared on writes as before.

## Alternatives considered

- Make Table.search/count build its cache key from something other than the query hash, for example by also including the query's path: Query objects are the cache key by design (ADR-3), and Table must not know query internals. The bug is an incomplete hash in one Query method, so the fix belongs there.
- Disable caching for fragment queries by setting the hash to None: This would fix the results but lose caching for fragment queries, and it would not give equal queries on the same path the same hash or make queries on different paths compare unequal. It also goes against C2, which says to include the path and all arguments in the hash.
- Audit and change all other Query methods too (Q-002 option b): The other methods already include self._path in their hashes, and the spec's default scope is fragment() only. Making the change wider is not needed.
- Clear the query cache on every search: This removes the cache feature and works around the problem instead of fixing the hash.

## Risks

- The spec marks FR-QFRAG-002 as an unconfirmed assumption (Q-001, priority P3). The fix delivers it anyway, because the hash change makes the queries unequal. If the maintainer wants the queries to stay equal, that would conflict with ADR-3, so this is unlikely.
- The fix changes the fragment hash shape, from a 2-tuple to a 3-tuple. Any existing test or user code that compares a fragment query's _hash to a literal tuple would break. A search of the repo's existing tests is advisable, but no such use is known.
- The root-level query Query().fragment({...}) now has the hash ('fragment', (), frozen). This stays consistent and hashable. A root query that is equal in both ways is only equal to another root query with the same fragment.
- Q-002 (other Query methods and deeper paths) is not examined beyond reading the source. Reading queries.py shows the other methods already include self._path, so no further change is planned. Deeper paths are covered because the whole _path tuple is hashed.

## Stage check: PASSED

