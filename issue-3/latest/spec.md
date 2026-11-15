# spec.md: Optional `limit` argument for Table.search() / TinyDB.search()

- Issue: #3 https://github.com/iDheer/tinydb/issues/3
- Verdict (A1 skill): **READY-WITH-OPEN-ITEMS**, stakeholder mode: unavailable

The issue is precise on the core behaviour: `search(cond, limit=N)` returns at most N matching documents, in the same order as today, and without `limit` nothing changes. Those three behaviours are STATED and READY. Edge-case values (0, negative, None, non-int), whether evaluation must stop early (the stated motivation), and the interaction with the internal query cache are not specified. They are recorded as P2/P3 questions and one candidate requirement, and they do not block the core. The current code (tinydb/table.py:249-297) caches the full result list per query. A naive implementation that caches a truncated list would make a later `search(q)` return too few documents, so that case is a candidate requirement and a risk. `TinyDB.search` is reached through `TinyDB.__getattr__` (database.py:251), which delegates to the default table. The issue text contains no instructions aimed at the agent. Stakeholder mode: unavailable (no maintainer comments).

## Requirements

### FR-SEARCH-001: When `search()` is called with a positive integer `limit`, the system shall return a list containing at most `limit` matching documents.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("returning at most 10 matching documents")
- Links: related: Q-003, related: Q-004, related: Q-005, related: GOAL-001, related: RSK-001
- Acceptance criteria:
  - **FR-SEARCH-001.AC-1**: Given a table with 25 documents of which 15 match Query().level == 'error', when table.search(Query().level == 'error', limit=10) is called, then the returned list has length 10 and every element satisfies level == 'error'.
  - **FR-SEARCH-001.AC-2**: Given a table with 3 documents matching Query().level == 'error', when table.search(Query().level == 'error', limit=10) is called, then the returned list has length 3 and contains all 3 matching documents.
  - **FR-SEARCH-001.AC-3**: Given a table in which exactly 10 documents match the query, when search(query, limit=10) is called, then the returned list has length 10.
  - **FR-SEARCH-001.AC-4**: Given a TinyDB instance (default table) with 15 matching documents, when db.search(Query().level == 'error', limit=10) is called, then the returned list has length 10 and no exception is raised.
  - **FR-SEARCH-001.AC-5**: Given a table with 15 matching documents where search(query) with no limit has already been called once, so the result is cached, when search(query, limit=10) is called with the same query, then the returned list has length 10.

### FR-SEARCH-002: When `search()` is called with `limit`, the system shall return the matching documents in the same relative order in which `search()` without `limit` returns them, so the result is the first `limit` documents of the unlimited result.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("in the same order `search()` returns them today")
- Links: related: Q-003
- Acceptance criteria:
  - **FR-SEARCH-002.AC-1**: Given a table with documents inserted in the order [{'n':1,'level':'error'}, {'n':2,'level':'info'}, {'n':3,'level':'error'}, {'n':4,'level':'error'}], when search(Query().level == 'error', limit=2) is called, then the result equals the first 2 elements of search(Query().level == 'error') called without limit, i.e. the documents with n == 1 and n == 3, in that order.
  - **FR-SEARCH-002.AC-2**: Given a table with 12 matching documents, when search(query, limit=5) is called, then the doc_ids of the result equal the first 5 doc_ids of search(query) without limit, in the same order.

### FR-SEARCH-003: When `search()` is called without a `limit` argument, the system shall behave exactly as it does today, returning all matching documents.
- Kind: FR · Priority: SHOULD · Status: **READY**
- Source: STATED ("Without `limit` it should behave exactly as it does now.")
- Links: related: Q-004, related: RSK-001
- Acceptance criteria:
  - **FR-SEARCH-003.AC-1**: Given a table with 15 matching documents, when search(query) is called without limit, then the returned list has length 15 and contains every matching document in insertion order.
  - **FR-SEARCH-003.AC-2**: Given a table where search(query) is called twice without limit, when the second call returns, then the result equals the first result and is a new list object (mutating it does not change a third call's result length).
  - **FR-SEARCH-003.AC-3**: Given a table with no matching documents, when search(query) is called without limit, then the returned value is an empty list.
  - **FR-SEARCH-003.AC-4**: Given the existing tinydb test-suite, when it is run unchanged, then all previously passing tests still pass.

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P2 | What should `search(cond, limit=0)` and `search(cond, limit=<negative>)` do? | limit=0 returns []; negative raises ValueError; both raise ValueError; limit=0 and negative mean no limit; negative behaves like a Python slice (default: limit=0 returns an empty list; a negative limit raises ValueError (ASM-002, PROVISIONAL)) | none yet (dimension 3: exceptions) |
| Q-002 | P3 | Should `limit=None` be accepted and treated as 'no limit', and what should a non-integer limit (e.g. '10', 2.5) do? | None = no limit; non-int raises TypeError; None = no limit; non-int is not validated; None is not accepted (default: limit=None means no limit; non-int values raise TypeError (ASM-003, PROVISIONAL)) | none yet (dimension 3: exceptions) |
| Q-003 | P2 | Is the performance motivation ('builds the full list every time') a requirement? Must `search(..., limit=N)` stop evaluating the condition on documents after the N-th match, or is it enough that the returned list is trimmed to N? | Only the result size is required (no efficiency requirement); Condition must not be evaluated on documents after the N-th match (testable by counting calls to a custom query callable); A time or memory threshold on a reference table size (stakeholder to supply) (default: No stakeholder-supplied threshold exists. Treat early termination as a SHOULD goal (GOAL-001), not a MUST requirement, until the maintainer answers.) | none yet (dimension 7: performance) |
| Q-004 | P2 | The query cache stores the full result of a `search(cond)`. If a limited search is run first, may a later unlimited `search(cond)` return only the limited subset? (The proposed answer is no.) And may a limited search on a cached query be served from the cache? | A limited search must never change what a later unlimited search returns (proposed); Limited searches bypass the cache entirely; Limited searches may populate the cache only when the full result is known (default: A limited search never changes later unlimited results (ASM-004, PROVISIONAL); the mechanism is left to the implementer.) | FR-SEARCH-004 |
| Q-005 | P3 | Should `limit` also be added to other read methods (`all()`, `count()`, `get()`) or to `Table.__iter__`? | Only search() (proposed); Also count(); Also all() (default: Only `search()` (out of scope otherwise)) | none yet (dimension 14: scope exclusions) |
| Q-006 | P3 | Should `limit` be a keyword-only argument or may it be passed positionally (`search(q, 10)`)? | Keyword form works; positional is unspecified; Keyword-only; Both (default: Only the keyword form `limit=N` is specified; positional use is unspecified.) | none yet (dimension 5: interfaces) |

## Terms

- TERM-001 **limit semantics for non-positive or non-integer values (0, negative, None, non-int)**: limit=None means 'no limit' (same as omitting it); limit=0 returns []; a negative value or a non-int raises ValueError/TypeError / limit=0 or negative means 'no limit' / limit=0 returns []; negative values behave like Python slicing, e.g. [:-1] / any non-positive value raises ValueError
- TERM-002 **"builds the full list every time" (efficiency motivation)**: Only the returned list is bounded: the result is trimmed to N and evaluation may still scan the whole table / Evaluation must stop once N matches are found, so the condition is not evaluated on the remaining documents / Memory use must be bounded by N
- TERM-003 **"most of the time I only need the first few matches" / "first"**: First in table iteration order (insertion order), which is what search() returns today / First by doc_id value

## Assumptions

- ASM-001: The requester (iDheer, repository owner) is the decision owner; there is a single stakeholder. The issue's polite request wording ('Could search() take…') is read as a feature request, not as COULD priority. The behavioural sentences are mapped as 'returning at most 10' → MUST and 'it should behave exactly as it does now' → SHOULD. (risk if wrong: Priorities would shift. This is informative only and does not change the verdict.)
- ASM-002: limit=0 returns []; a negative limit raises ValueError (provisional, Q-001). (risk if wrong: Callers passing 0 or a negative number may get a different result or exception than they expect.)
- ASM-003: limit=None is equivalent to omitting limit; a non-int limit raises TypeError (provisional, Q-002). (risk if wrong: The signature and error behaviour for odd inputs would differ from what the maintainer wants.)
- ASM-004: A limited search must not alter the results of later unlimited searches on the same query (provisional, Q-004). (risk if wrong: If the maintainer accepts cache-affected results, FR-SEARCH-004 would be rejected. Otherwise a cache-poisoning bug could ship.)

## Out of scope

- Adding `limit` (or offset/pagination) to `all()`, `count()`, `get()`, `update()`, `remove()` or to `Table.__iter__` (Q-005, not requested)
- An `offset` or `skip` argument, and pagination or cursors
- Sorting or reordering of search results; order stays as today
- Changing the query cache design beyond what is needed to keep unlimited searches unchanged
- Candidate requirement FR-SEARCH-004 (not agreed): if a limited `search(cond, limit=N)` is run before an unlimited `search(cond)` on the same table and query, the unlimited call shall still return all matching documents. Source ASSUMED (ASM-004, Q-004). Status ASSUMPTION-ONLY/NEEDS-CLARIFICATION (Q-004). AC FR-SEARCH-004.AC-1: Given a fresh table with 15 documents matching query q, when search(q, limit=3) is called and then search(q), then the second call returns 15 documents. AC FR-SEARCH-004.AC-2: Given a table where search(q, limit=3) was called, when a new matching document is inserted and search(q) is called, then the result includes all 16 matching documents.
- GOAL-001 (traced, not tested): reduce the cost of getting a few matches from a ~50k-entry table, per 'builds the full list every time' (TERM-002, Q-003). RSK-001: a limit implementation that caches a truncated result list would corrupt later unlimited searches (trigger: limited call before unlimited call on a cacheable query; likelihood M; impact H; affects FR-SEARCH-003, FR-SEARCH-004). Related: the docstring at table.py:253-257 notes cached documents are shared objects; documents returned by a limited search are subject to the same read-only caveat.
- Dependency DEP-001: TinyDB.__getattr__ (database.py:251) delegates `db.search` to the default table, so AC FR-SEARCH-001.AC-4 depends on the Table.search signature being forwarded unchanged.

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|
| FR-SEARCH-001.AC-1 | yes | Concrete starting state (25 documents, 15 matching), one search call with limit=10, and observable outcomes (length 10, all elements match). |
| FR-SEARCH-001.AC-2 | yes | Concrete state of 3 matching documents with limit=10, and the result length and membership are directly assertable. |
| FR-SEARCH-001.AC-3 | yes | Exactly 10 matching documents with limit=10 gives a precise, assertable result length of 10. |
| FR-SEARCH-001.AC-4 | yes | A default-table TinyDB with 15 matches, one db.search call with limit=10, and observable outcomes (length 10, no exception). |
| FR-SEARCH-001.AC-5 | yes | The cached state is produced by a concrete prior unlimited search, and the limited search result length of 10 is directly assertable. |
| FR-SEARCH-002.AC-1 | yes | Given a fixed insertion order, the expected result (documents n==1 and n==3 in that order) is fully specified and comparable to the unlimited search's first two elements. |
| FR-SEARCH-002.AC-2 | yes | Comparing doc_ids of the first 5 results of a limited search against the first 5 of an unlimited search is a precise, automatable equality check. |
| FR-SEARCH-003.AC-1 | yes | An unlimited search over 15 matching documents has a precise expected length of 15 and an insertion-order membership check. |
| FR-SEARCH-003.AC-2 | yes | Equality of two unlimited results and independence of the returned list (a later call's length is unaffected by mutating the earlier list) can be asserted, though the specific mutation is left to the test author. |
| FR-SEARCH-003.AC-3 | yes | A search with no matching documents must return an empty list, a precise and assertable value. |
| FR-SEARCH-003.AC-4 | yes | Running the existing pytest suite unchanged and checking that previously passing tests still pass is an automated, objective check. |

## Stage check: PASSED

