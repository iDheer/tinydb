# spec.md: Query.one_of() must match every document when given a generator

- Issue: #2 https://github.com/iDheer/tinydb/issues/2
- Verdict (A1 skill): **READY-WITH-OPEN-ITEMS**, stakeholder mode: unavailable

Precise bug report. In tinydb/queries.py:476-487 `one_of` evaluates `value in items` per document. A generator is consumed by the first membership tests, so later documents are compared against an exhausted generator and fail. The issue's example returns [a, b] instead of [a, b, a]. Two core requirements are READY: (1) a generator argument gives the same results as the equivalent list, whatever the document order; (2) list behaviour is unchanged. Open items are P2/P3 only: reuse of the same query object, other iterables, an empty generator, and the docs. Stakeholder mode is unavailable and no maintainer comments were provided. No network tools were used: no tool-answerable questions. The issue text contained no embedded instructions. Verdict: READY-WITH-OPEN-ITEMS.

## Requirements

### FR-QUERY-001: When Query.one_of is given a generator of allowed values, the resulting query shall match every document whose tested field value is one of the generated values, independent of how many documents were tested before it.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("Check if the value is contained in a list or generator. / expected: [{'tag': 'a'}, {'tag': 'b'}, {'tag': 'a'}]")
- Links: related: Q-001, related: Q-002, related: Q-003, TERM-001
- Acceptance criteria:
  - **FR-QUERY-001.AC-1**: Given a TinyDB with MemoryStorage holding [{'tag':'a'},{'tag':'b'},{'tag':'a'},{'tag':'c'}] and allowed = (t for t in ['a','b']), when db.search(Query().tag.one_of(allowed)) is called, then the result equals [{'tag':'a'},{'tag':'b'},{'tag':'a'}].
  - **FR-QUERY-001.AC-2**: Given q = Query().key1.one_of(v for v in ['value 1','value 2']), when q is called directly on {'key1':'value 1'}, then {'key1':'value 2'}, then {'key1':'value 1'}, in that order, then all three calls return True.
  - **FR-QUERY-001.AC-3**: Given q = Query().key1.one_of(v for v in ['value 1','value 2']), when q is called on {'key1':'value 3'}, then it returns False.
  - **FR-QUERY-001.AC-4**: Given documents [{'tag':'b'},{'tag':'a'},{'tag':'a'}] and a generator yielding 'a' then 'b', when db.search(Query().tag.one_of(generator)) is called, then the result equals [{'tag':'b'},{'tag':'a'},{'tag':'a'}] (order of the generated values does not affect which documents match).

### FR-QUERY-002: When Query.one_of is given a list of allowed values, the resulting query shall keep matching exactly the documents whose tested field value is in the list.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("With a list it works fine.")
- Links: related: Q-002
- Acceptance criteria:
  - **FR-QUERY-002.AC-1**: Given q = Query().key1.one_of(['value 1','value 2']), when q is called on {'key1':'value 1'}, {'key1':'value 2'} and {'key1':'value 3'}, then it returns True, True and False respectively.
  - **FR-QUERY-002.AC-2**: Given a TinyDB with MemoryStorage holding [{'tag':'a'},{'tag':'b'},{'tag':'a'},{'tag':'c'}], when db.search(Query().tag.one_of(['a','b'])) is called, then the result equals [{'tag':'a'},{'tag':'b'},{'tag':'a'}].

### FR-QUERY-003: If the same query object built with a generator is used for more than one search (Q-001), the system shall return the same documents each time.
- Kind: FR · Priority: UNSET · Status: **ASSUMPTION-ONLY**
- Source: ASSUMED ("")
- Links: ASM-001, Q-001
- Acceptance criteria:
  - **FR-QUERY-003.AC-1**: Given a TinyDB holding [{'tag':'a'},{'tag':'b'},{'tag':'c'}] and q = Query().tag.one_of(t for t in ['a','b']), when db.search(q) is called twice, then both results equal [{'tag':'a'},{'tag':'b'}] (to be confirmed by Q-001).

### FR-QUERY-004: If an empty generator is passed to one_of (Q-003), the system shall match no document.
- Kind: FR · Priority: UNSET · Status: **ASSUMPTION-ONLY**
- Source: ASSUMED ("")
- Links: ASM-002, Q-003
- Acceptance criteria:
  - **FR-QUERY-004.AC-1**: Given a document {'tag':'a'} and q = Query().tag.one_of(t for t in []), when q is called on the document, then it returns False.

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P2 | Should a query object built with a generator give the same results when it is reused for several searches, or is it single-use? | (a) reuse must give the same results every time; (b) a generator query is single-use and this is documented (default: (a), recorded as ASM-001 (PROVISIONAL)) | FR-QUERY-003 |
| Q-002 | P3 | Should one_of also accept other non-list iterables (set, tuple, range, map/iterator) and the type hint/documentation be updated to match? | (a) generators only; docstring/type hint fixed; (b) any iterable; (c) no doc change (default: (a), as stated in the issue; docs left to the implementer) | none yet |
| Q-003 | P3 | What should one_of match when given an empty generator? | (a) matches no document; (b) other (default: (a), recorded as ASM-002 (PROVISIONAL)) | FR-QUERY-004 |

## Terms

- TERM-001 **generator**: A generator object or generator expression only (as in the issue example). This is the stated case. / Any one-shot iterator, such as map(), filter() or iter(list). It has the same exhaustion problem. / Any iterable, including sets, tuples, ranges and dict views. The docstring says only 'list or generator'.
- TERM-002 **matches only some of the documents**: Documents tested after the generator is exhausted are rejected. This is the observed symptom: the third document {'tag':'a'} is dropped.

## Assumptions

- ASM-001: A query object built with a generator is expected to be reusable across searches, with the same results each time. (risk if wrong: If single-use semantics are intended, FR-QUERY-003 would be wrong. Also, query-cache or hash behaviour keyed on the generator object could then differ.)
- ASM-002: An empty generator behaves like an empty list: no document matches. (risk if wrong: Low: it is the natural membership semantics.)
- ASM-003: The requester and maintainer (iDheer) decides, and the reported behaviour is a bug rather than intended: the docstring says 'list or generator'. (risk if wrong: If generators were never meant to be supported, the fix would be a documentation or type change instead.)

## Out of scope

- Choosing the implementation (for example materialising the generator once, versus other approaches).
- Changes to other Query methods such as any(), all() and test().
- Changes to query hashing or equality semantics, beyond what FR-QUERY-001 requires.
- Support for iterables other than list and generator, pending Q-002.
- Changelog or release notes.

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|
| FR-QUERY-001.AC-1 | yes | Concrete starting database, a single db.search call with a generator-based one_of, and an exact expected list of documents. |
| FR-QUERY-001.AC-2 | yes | Concrete query and a fixed sequence of three direct calls with exact inputs, each with an explicit expected boolean result (all True). |
| FR-QUERY-001.AC-3 | yes | Concrete query and input document with an explicit expected return value of False. |
| FR-QUERY-001.AC-4 | yes | Concrete documents and generator values, one db.search call, and an exact expected result list in original document order. |
| FR-QUERY-002.AC-1 | yes | Concrete list-based query called on three specified documents, each with an explicit expected boolean (True, True, False). |
| FR-QUERY-002.AC-2 | yes | Concrete database contents and a single db.search call with an exact expected list result. |

## Stage check: PASSED

