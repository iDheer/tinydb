# spec.md: Optional `limit` argument for search()

- Issue: #3 https://github.com/iDheer/tinydb/issues/3
- Verdict (A1 skill): **READY-WITH-OPEN-ITEMS**, stakeholder mode: unavailable

Precise feature request: `search(cond, limit=N)` returns at most N matching documents in the same order as today; omitting `limit` must leave behaviour unchanged. I read tinydb/table.py: `Table.search(self, cond)` has no `limit` today. It returns a fresh list copy of cached results, and caches cacheable queries. `TinyDB.search` is forwarded to the default table through `__getattr__` (database.py:251). That makes cache interaction an observable concern: a limited search must not change what a later unlimited search returns. The previous draft failed on FR-SRCH-003.AC-2 ('existing calls' had no baseline). Both FR-SRCH-003 criteria now use a fixed table (five documents, n=1..5) and literal expected values, so they have no hidden baseline. Edge-case inputs (limit=0, negative, non-int, None) and whether evaluation must stop early are P2/P3 questions that block no stated behaviour. Stakeholder mode is unavailable, so the verdict is READY-WITH-OPEN-ITEMS: all core requirements are READY and no P1 question or conflict is open.

## Requirements

### FR-SRCH-001: The system shall let Table.search accept an optional `limit` argument and, when a positive integer `limit` is given, return at most `limit` matching documents.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("returning at most 10 matching documents")
- Links: related: Q-001, related: Q-002, related: Q-003, related: GOAL-1
- Acceptance criteria:
  - **FR-SRCH-001.AC-1**: Given a fresh in-memory table (TinyDB(storage=MemoryStorage).table('t')) holding five documents {'n':1}..{'n':5} inserted in that order, and cond = Query().n >= 1 (all five match), when table.search(cond, limit=2) is called, then the returned list has length 2.
  - **FR-SRCH-001.AC-2**: Given the same fixture and cond, where table.search(cond) was already called once without limit (so the result is held in the query cache), when table.search(cond, limit=2) is called, then the returned list has length 2 and equals [{'n':1},{'n':2}].
  - **FR-SRCH-001.AC-3**: Given the same fixture and a fresh cond = Query().n >= 1, when table.search(cond, limit=1) is called, then the returned list has length 1 and its element has doc_id 1 and content {'n':1}.

### FR-SRCH-002: The system shall return the documents of a limited search in the same relative order in which search() without `limit` returns them.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("in the same order `search()` returns them today")
- Links: related: TERM-2
- Acceptance criteria:
  - **FR-SRCH-002.AC-1**: Given a fresh in-memory table holding documents {'n':1}..{'n':5} inserted in that order (doc_ids 1..5), and cond = Query().n >= 1, when table.search(cond, limit=3) is called, then the returned documents have doc_ids [1, 2, 3] and contents [{'n':1},{'n':2},{'n':3}], in that order.
  - **FR-SRCH-002.AC-2**: Given the same fixture, and a second fresh table built identically for the baseline, when table.search(cond, limit=3) is called on the first and table.search(cond)[:3] on the second, then the two lists are equal element by element, including doc_id.

### FR-SRCH-003: The system shall return, for a call to search without a `limit` argument, the same result it returned before the `limit` argument was introduced.
- Kind: FR · Priority: SHOULD · Status: **READY**
- Source: STATED ("Without `limit` it should behave exactly as it does now.")
- Links: related: TERM-3, related: ASM-002
- Acceptance criteria:
  - **FR-SRCH-003.AC-1**: Given a fresh in-memory table holding documents {'n':1}..{'n':5} inserted in that order (doc_ids 1..5), when table.search(Query().n >= 3) is called with no `limit` argument, then the result is a list of exactly three Document objects with doc_ids [3, 4, 5] and contents [{'n':3},{'n':4},{'n':5}], in that order.
  - **FR-SRCH-003.AC-2**: Given the same fixture and one Query object cond = Query().n >= 1, when table.search(cond) is called twice with no `limit` argument, giving results r1 and r2, then r1 and r2 each have doc_ids [1, 2, 3, 4, 5] and contents [{'n':1}..{'n':5}], and r1 is not r2 (the second call returns a new list object).

### FR-SRCH-004: The system shall return the complete list of matching documents from a search without `limit` that is made after a search with `limit` using the same condition.
- Kind: FR · Priority: SHOULD · Status: **READY**
- Source: DERIVED ("Without `limit` it should behave exactly as it does now. (parent: FR-SRCH-003; a limited result left in the query cache would make a later unlimited search differ from today's behaviour)")
- Links: parent: FR-SRCH-003
- Acceptance criteria:
  - **FR-SRCH-004.AC-1**: Given a fresh in-memory table holding documents {'n':1}..{'n':5} inserted in that order, and one Query object cond = Query().n >= 1 on which no search has yet been made, when table.search(cond, limit=2) is called and then table.search(cond) is called, then the second call returns five documents with doc_ids [1, 2, 3, 4, 5].

### FR-SRCH-005: The system shall return all matching documents when the positive integer `limit` is greater than or equal to the number of matches.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: DERIVED ("returning at most 10 matching documents (parent: FR-SRCH-001; 'at most' means fewer matches are returned as they are, not padded or refused)")
- Links: parent: FR-SRCH-001
- Acceptance criteria:
  - **FR-SRCH-005.AC-1**: Given a fresh in-memory table holding documents {'n':1}..{'n':5} inserted in that order, and cond = Query().n <= 3 (three match), when table.search(cond, limit=10) is called, then the result has doc_ids [1, 2, 3] and contents [{'n':1},{'n':2},{'n':3}].
  - **FR-SRCH-005.AC-2**: Given the same fixture and cond = Query().n <= 3, when table.search(cond, limit=3) is called, then the result has doc_ids [1, 2, 3].

### FR-SRCH-006: The system shall accept the `limit` argument on search() called on a TinyDB instance, which operates on its default table.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("db.search(Query().level == 'error', limit=10)")
- Links: related: Q-001
- Acceptance criteria:
  - **FR-SRCH-006.AC-1**: Given db = TinyDB(storage=MemoryStorage) with five documents {'level':'error','n':1}..{'level':'error','n':5} inserted in that order into the default table, when db.search(Query().level == 'error', limit=2) is called, then the result is a list of two documents with contents [{'level':'error','n':1},{'level':'error','n':2}], in that order.
  - **FR-SRCH-006.AC-2**: Given the same db, when db.search(Query().level == 'error') is called with no `limit`, then the result contains all five documents in insertion order.

### FR-SRCH-007: The system shall define the behaviour of search() when `limit` is 0, negative, None, or not an integer.
- Kind: FR · Priority: UNSET · Status: **NEEDS-CLARIFICATION**
- Source: ASSUMED ("")
- Links: blocked by: Q-001, Q-002, ASM-001
- Acceptance criteria:
  - **FR-SRCH-007.AC-1**: Given a fresh in-memory table holding documents {'n':1}..{'n':5} and cond = Query().n >= 1, when table.search(cond, limit=<TBD: Q-001>) is called, then <TBD: Q-001>.

### FR-SRCH-008: The system shall stop evaluating the query against further documents once `limit` matches have been found.
- Kind: FR · Priority: UNSET · Status: **NEEDS-CLARIFICATION**
- Source: ASSUMED ("")
- Links: blocked by: Q-003, GOAL-1, ASM-003
- Acceptance criteria:
  - **FR-SRCH-008.AC-1**: Given a fresh in-memory table holding documents {'n':1}..{'n':5} and a counting condition object that records each document it is called on, when table.search(cond, limit=2) is called, then <TBD: Q-003>.

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P2 | What should search() do when `limit` is 0, negative, or not an integer (e.g. 1.5, '10', True)? | (a) limit=0 returns []; negative or non-int raises ValueError/TypeError; (b) any non-positive limit raises ValueError; (c) negative values follow Python slice semantics (default: (a), recorded as ASM-001 (PROVISIONAL)) | FR-SRCH-007 |
| Q-002 | P3 | Should an explicit `limit=None` be accepted and mean 'no limit'? | (a) yes, same as omitting the argument; (b) no, raises TypeError (default: (a), recorded as ASM-001 (PROVISIONAL)) | FR-SRCH-007 |
| Q-003 | P2 | The issue complains that `db.search(q)[:10]` 'builds the full list every time'. Must a limited search also avoid evaluating the query on documents after the limit-th match, or is returning the right result enough? | (a) early termination required: cond is called on no more documents than needed to find `limit` matches on an uncached query; (b) only the returned result is specified; performance is a goal, not a requirement (default: (b), recorded as ASM-003 (PROVISIONAL), with FR-SRCH-008 kept as an unagreed candidate) | FR-SRCH-008 |
| Q-004 | P3 | Who decides on this feature (the requester iDheer, or another maintainer)? | the requester; another maintainer (default: the requester decides (ASM-004)) | none yet |

## Terms

- TERM-1 **limit (value semantics)**: A positive integer maximum count; 0, negative, None and non-integer values are errors / limit=0 returns [] and limit=None means no limit; negatives are errors / Python slice semantics (negative counts from the end)
- TERM-2 **same order search() returns them today**: The order of documents in the table's stored mapping (insertion order, doc_id ascending in the normal case) as returned by search() without limit / Ascending doc_id order regardless of storage order
- TERM-3 **behave exactly as it does now**: Same return value (type, documents, doc_ids, order, fresh list copy) for the same inputs; this is what the acceptance criteria test / Additionally the same internal side effects (cache content, number of condition calls)
- TERM-4 **first few matches**: The first N matches in the order search() returns them (what FR-SRCH-002 covers) / Any N matches, with no guarantee of position

## Assumptions

- ASM-001: For limit values outside the positive-integer range (0, negative, None, non-int), the provisional behaviour is: 0 returns [], None means no limit, negative or non-int values raise an error. (risk if wrong: Callers relying on a different convention (e.g. slice semantics or an error for 0) would be surprised; only FR-SRCH-007 is affected.)
- ASM-002: 'Behave exactly as it does now' is read as the observable return value (list type, Document objects, doc_ids, order, fresh copy per call), not internal side effects (TERM-3). (risk if wrong: If internal side effects such as cache contents or condition-call counts are meant to be identical, FR-SRCH-003 would need more acceptance criteria.)
- ASM-003: Early termination of query evaluation is not required; the issue's performance remark is a motivation (GOAL-1) and not a testable requirement. (risk if wrong: If early termination is required, FR-SRCH-008 becomes core and a simple slice of the full result would not satisfy the issue.)
- ASM-004: The issue author is the decision owner for this feature and no other stakeholders exist. (risk if wrong: A maintainer may reject or change the API (e.g. a different argument name), invalidating the acceptance criteria that call `limit=`.)

## Out of scope

- Adding `limit` to other methods (Table.all, Table.get, Table.count, Table.update, Table.remove, etc.): the issue only names search().
- Offset or pagination arguments, and sorting or reordering of results.
- Changing the result order of search() without `limit`.
- Changing the query cache design beyond what FR-SRCH-004 requires of its observable behaviour; this stage does not design the fix.
- Performance targets or benchmarks for a 50k-document table: no numbers were given (see Q-003).
- Changes to storage backends or the CLI the author mentions.

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|
| FR-SRCH-001.AC-1 | yes | Concrete fixture, one search with limit=2, and an observable result length of 2. |
| FR-SRCH-001.AC-2 | yes | Specifies a prior unlimited search to populate the cache, then a limit=2 search with an exact expected list of contents. |
| FR-SRCH-001.AC-3 | yes | Fresh query with limit=1 has an exact expected length, doc_id and content. |
| FR-SRCH-002.AC-1 | yes | Fixed fixture and limit=3 yield exact doc_ids [1,2,3] and contents in order. |
| FR-SRCH-002.AC-2 | yes | Compares a limited search against a slice of an unlimited search on an identically built table, giving a deterministic element-by-element check. |
| FR-SRCH-003.AC-1 | yes | No-limit search with a fixed fixture gives exact doc_ids, contents, order and Document type. |
| FR-SRCH-003.AC-2 | yes | Two identical unlimited searches can be checked for equal contents, doc_ids and object identity (r1 is not r2). |
| FR-SRCH-004.AC-1 | yes | A limited search followed by an unlimited search on the same Query object has a deterministic expected doc_id list of five documents. |
| FR-SRCH-005.AC-1 | yes | Limit larger than the match count returns exactly the three matching documents with exact doc_ids and contents. |
| FR-SRCH-005.AC-2 | yes | Limit equal to the match count returns exactly doc_ids [1,2,3], which is a concrete check. |
| FR-SRCH-006.AC-1 | yes | db-level search with a limit on a fixed fixture yields exact contents in insertion order. |
| FR-SRCH-006.AC-2 | yes | Unlimited db-level search on the same fixture can be checked for all five documents in insertion order. |

## Stage check: PASSED

