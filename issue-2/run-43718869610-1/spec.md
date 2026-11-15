# spec.md: Query.one_of() must match all documents when given a generator

- Issue: #2 https://github.com/iDheer/tinydb/issues/2
- Verdict (A1 skill): **READY-WITH-OPEN-ITEMS**, stakeholder mode: unavailable

Precise bug report. Currently `Query.one_of(items)` (tinydb/queries.py:476) runs `value in items` once per document. `freeze()` leaves a generator unchanged, so the generator is a one-shot iterator that is consumed by the first documents tested. Later documents then see an exhausted generator and fail to match; in the issue's example the second `'a'` is missing. The issue states the expected result for the example (all three matching documents) and says the list case already works. Two requirements are READY: generator support, and no change for lists. One candidate requirement (reusing one query object for several searches) is recorded as not agreed. Only P3 questions remain, and stakeholder mode is unavailable (no maintainer comments), so the verdict is READY-WITH-OPEN-ITEMS. No instructions were found inside the untrusted issue text. No tools were needed for evidence: nothing public and named is involved.

## Requirements

### FR-QUERY-001: When a generator is passed to Query.one_of, the query shall match every document whose tested field value is contained in the values the generator yields, with no document missed because earlier documents were tested.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("expected: [{'tag': 'a'}, {'tag': 'b'}, {'tag': 'a'}]")
- Links: TERM-001, Q-001, Q-002, RSK-001, related: Q-001, Q-002
- Acceptance criteria:
  - **FR-QUERY-001.AC-1**: Given a TinyDB on MemoryStorage holding the documents {'tag':'a'}, {'tag':'b'}, {'tag':'a'}, {'tag':'c'} and allowed = (t for t in ['a','b']), when db.search(Query().tag.one_of(allowed)) is called once, then the result equals [{'tag':'a'}, {'tag':'b'}, {'tag':'a'}].
  - **FR-QUERY-001.AC-2**: Given q = Query().tag.one_of(t for t in ['a','b']), when q is called directly with {'tag':'a'}, {'tag':'b'}, {'tag':'a'} and {'tag':'c'} in that order, then the return values are True, True, True, False.
  - **FR-QUERY-001.AC-3**: Given a TinyDB on MemoryStorage holding {'tag':'a'}, {'tag':'a'}, {'tag':'b'} and a generator yielding 'a' and 'b', when db.count(Query().tag.one_of(generator)) is called, then the count is 3.

### FR-QUERY-002: When a list is passed to Query.one_of, the query shall keep matching every document whose tested field value is in the list.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("With a list it works fine.")
- Links: related: Q-002
- Acceptance criteria:
  - **FR-QUERY-002.AC-1**: Given a TinyDB on MemoryStorage holding {'tag':'a'}, {'tag':'b'}, {'tag':'a'}, {'tag':'c'}, when db.search(Query().tag.one_of(['a','b'])) is called, then the result equals [{'tag':'a'}, {'tag':'b'}, {'tag':'a'}].
  - **FR-QUERY-002.AC-2**: Given q = Query().key1.one_of(['value 1','value 2']), when q is called with {'key1':'value 1'} and then with {'key1':'value 3'}, then the results are True and False.
  - **FR-QUERY-002.AC-3**: Given the list ['a','b'] and a query q = Query().tag.one_of(['a','b']) used in two successive db.search calls, when both searches run against documents {'tag':'a'}, {'tag':'c'}, then both results equal [{'tag':'a'}].

### FR-QUERY-003: If a single one_of query built from a generator is used in more than one search (Q-001), the system shall return the same matches for each search.
- Kind: FR · Priority: UNSET · Status: **ASSUMPTION-ONLY**
- Source: ASSUMED ("")
- Links: ASM-002, Q-001, RSK-001
- Acceptance criteria:
  - **FR-QUERY-003.AC-1**: Given documents {'tag':'a'}, {'tag':'c'} and q = Query().tag.one_of(t for t in ['a','b']), when db.search(q) is called twice in a row on the same TinyDB, then both calls return [{'tag':'a'}].
  - **FR-QUERY-003.AC-2**: Given q = Query().tag.one_of(t for t in ['a','b']) used on two separate TinyDB instances holding {'tag':'a'}, when db1.search(q) and then db2.search(q) are called, then both return [{'tag':'a'}].

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P3 | When the same query object built from a generator is used in more than one search, must every search return the same matches (the generator is one-shot, so a second use would otherwise see no values)? | (a) yes, repeated use gives identical results; (b) only a single use is required; (c) repeated use may raise a clear error (default: (a), recorded as ASM-002 (PROVISIONAL)) | FR-QUERY-003 |
| Q-002 | P3 | Should other non-list iterables (iterators such as map/filter/iter(), sets, tuples, ranges) also be supported by one_of, or only generators and lists? | (a) generators and lists only; (b) any iterable; (c) generators, lists and other collections already supported today (default: (a), recorded as ASM-003 (PROVISIONAL); other iterables stay out of scope) | none yet (dimension 3, 14) |
| Q-003 | P3 | Is the same generator problem expected to be fixed for Query.any and Query.all, which also accept a sequence argument? | (a) one_of only; (b) one_of, any and all (default: (a); any and all are recorded as out of scope) | none yet (dimension 14) |

## Terms

- TERM-001 **generator**: A generator expression or generator-function result, as in the issue example `(t for t in ['a','b'])`. This is the reading the issue actually shows. / Any one-shot iterator (map, filter, file object, iter(...)). The same consumption problem applies, but the issue does not name these. / Any non-list iterable (set, tuple, range, dict view). These can be iterated more than once, so they are a different case from a generator.
- TERM-002 **works fine / matches only some (priority-word mapping)**: Declarative statements about behaviour ('With a list it works fine', 'expected: ...') map to MUST per the skill's priority rule. No 'should/could' wording is present, so none map to SHOULD or COULD.

## Assumptions

- ASM-001: The requester (the issue author, iDheer) is the decision owner for this change. No maintainer comments are included, so the stakeholder mode is unavailable and every open question stays OPEN. (risk if wrong: A maintainer may decide scope differently, for example by also covering any and all.)
- ASM-002: A user who builds a query from a generator expects it to behave consistently if the query object is reused (FR-QUERY-003). (risk if wrong: If one-time use is acceptable, FR-QUERY-003 should be rejected and withdrawn. If reuse is expected, tests that only check a single search would miss the bug.)
- ASM-003: Scope is limited to generators and lists, the two types named in the docstring and the issue. (risk if wrong: Other iterators such as map/filter objects would still fail silently after the fix.)

## Out of scope

- Changing the behaviour of Query.any and Query.all (see Q-003); no change was requested for them.
- Supporting arbitrary other iterables or iterators beyond generators and lists, unless Q-002 is answered otherwise.
- Changing the type hint, docstring or docs/usage.rst wording for one_of, unless the maintainer asks; the issue treats the docstring as the existing contract.
- Design of the fix (for example materialising the generator into a collection when the query is built). This is left to the implementation stage.
- Query result caching design. Recorded only as RSK-001: freeze() does not freeze a generator, so the query hash depends on the generator object itself. This was read in tinydb/utils.py:150-169, and the effect is not tested.

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|
| FR-QUERY-001.AC-1 | yes | Concrete starting state (MemoryStorage with four named documents and a named allowed sequence), a single db.search call, and an exact expected list of documents. |
| FR-QUERY-001.AC-2 | yes | Query q is built from a named generator and called directly on four named documents in a stated order, with exact expected boolean return values. |
| FR-QUERY-001.AC-3 | yes | Concrete documents and a named generator yielding 'a' and 'b' with a single db.count call and an exact expected count of 3. |
| FR-QUERY-002.AC-1 | yes | Concrete documents, a single db.search call with a literal list, and an exact expected result list. |
| FR-QUERY-002.AC-2 | yes | Query with a literal list is called on two named documents, and the expected results True and False are exact and observable. |
| FR-QUERY-002.AC-3 | yes | Concrete list, documents and expected result are given; the two successive searches are a repeated use of one query, and the expected outcome for both is exact. |

## Stage check: PASSED

