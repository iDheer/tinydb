# design.md

Make Query.one_of() materialise a one-shot iterator (generator) into a tuple when the query is built, so the per-document `value in items` test and the query hash both use a reusable collection.

## Approach

In `Query.one_of` (tinydb/queries.py:476), before building the test, add: if `items` is an `collections.abc.Iterator` (generators are one; lists, tuples and sets are not), replace it with `tuple(items)`. Both the lambda `value in items` and `freeze(items)` in the hash then use the materialised tuple. Lists and other collections are untouched (FR-QUERY-002). Because the generator is consumed once at construction, the query can be reused across searches and TinyDB instances (FR-QUERY-003). The hash becomes content-based (`('one_of', path, ('a','b'))`) rather than depending on generator object identity (RSK-001), so C2 is satisfied and two one_of queries with the same values correctly share a hash. This needs a stdlib import (`from collections.abc import Iterator`) at the top of queries.py, and a small update to the type hint/docstring if desired (the spec says the docstring stays unchanged, so leave it).

## Files and symbols to change

| File | Change | Symbol | Kind | Symbol change | What |
|---|---|---|---|---|---|
| `tinydb/queries.py` | modify | `Query.one_of` | method | modify | If `items` is a collections.abc.Iterator, set `items = tuple(items)` before creating the test lambda and the hash `('one_of', self._path, freeze(items))`. Lists and other collections pass through unchanged. |

## Acceptance criteria → code → test

| AC | Symbols | Test idea |
|---|---|---|
| FR-QUERY-001.AC-1 | Query.one_of | TinyDB(storage=MemoryStorage) with a,b,a,c; db.search(Query().tag.one_of(t for t in ['a','b'])) == [a,b,a]. |
| FR-QUERY-001.AC-2 | Query.one_of | Build q from a generator; call q on a,b,a,c docs in order; assert True,True,True,False. |
| FR-QUERY-001.AC-3 | Query.one_of | Docs a,a,b with a generator yielding a,b; db.count(Query().tag.one_of(gen)) == 3. |
| FR-QUERY-002.AC-1 | Query.one_of | Search with list ['a','b'] over a,b,a,c returns [a,b,a]. |
| FR-QUERY-002.AC-2 | Query.one_of | q = Query().key1.one_of(['value 1','value 2']); q({'key1':'value 1'}) is True, q({'key1':'value 3'}) is False. |
| FR-QUERY-002.AC-3 | Query.one_of | Use one list-based query in two db.search calls on a,c docs; both return [a]. |
| FR-QUERY-003.AC-1 | Query.one_of | Generator-based q searched twice on the same db (a,c docs); both results are [a] (the second call is also checked after clearing the cache with an insert). |
| FR-QUERY-003.AC-2 | Query.one_of | Same generator-based q searched on two separate MemoryStorage TinyDBs holding {'tag':'a'}; both return [a]. |

## Architecture constraints (ARCHITECTURE.md)

- C2: one_of still goes through Query._generate_test and keeps the hash ('one_of', path, freeze(items)); after materialisation the hash encodes the actual values instead of a generator object identity, so equal-meaning queries share a hash and different ones do not.
- C4: Only a stdlib import (collections.abc) is added to queries.py; no import of table.py or database.py.
- C5: Uses only the standard library (collections.abc.Iterator, built-in tuple).
- C3: Not affected: no change to Table or storage writes.

## Alternatives considered

- Make `freeze()` in utils.py convert generators/iterators to tuples: Wider blast radius: freeze is used by every query operation, and the lambda in one_of would still iterate the original, already-consumed generator unless one_of also uses the frozen value. It would also be a larger change than needed.
- Test with `any(value == x for x in items)` or re-create the iterator per document: A generator cannot be re-iterated, so this does not solve it. It would also leave the second search with an empty generator (FR-QUERY-003).
- Materialise every `items` with `tuple(items)` unconditionally: Changes the behaviour of the list and set cases (set membership becomes O(n), the type changes) and conflicts with FR-QUERY-002 'no change for lists'. Restricting to Iterator keeps the change minimal.
- Also fix Query.any and Query.all: Out of scope per spec (Q-003 default (a)); they accept a list or a query, not a generator per their type hints.
- Restrict to `types.GeneratorType` instead of `Iterator`: Viable and equally small, but Iterator also fixes map/filter/iter() objects, which would otherwise fail silently in the same way; Q-002 leaves this open and the extra coverage is harmless.

## Risks

- The spec says 'generator' (TERM-001) but Iterator-based detection also materialises map/filter/iter()/file objects. This is a harmless superset, but it goes beyond the default for Q-002 (a); worth noting for the reviewer.
- An infinite generator would now hang at query construction rather than at match time. The only previous behaviour was undefined/partial matches, so this is acceptable.
- A generator is consumed at build time, so a caller who later expects to reuse that generator will find it exhausted. This is inherent to generators.
- FR-QUERY-003 is ASSUMPTION-ONLY (Q-001 open); the chosen design satisfies it for free, but the spec would still need maintainer confirmation.
- The type hint `items: list[Any]` and docstring are left as-is per spec; mypy treats generators as not matching the hint, so only callers' type checkers could complain. Out of scope per spec.
- Query.any and Query.all have the same latent issue if given generators; intentionally untouched (Q-003).

## Stage check: PASSED

