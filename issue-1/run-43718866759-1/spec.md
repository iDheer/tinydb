# spec.md: fragment() on a nested field returns the results of a different field

- Issue: #1 https://github.com/iDheer/tinydb/issues/1
- Verdict (A1 skill): **READY-WITH-OPEN-ITEMS**, stakeholder mode: unavailable

A precise bug report. `Query.fragment()` (tinydb/queries.py:489-501) builds its query hash as `('fragment', freeze(document))` and leaves out `self._path`. The other path-based tests I read (`==`, `any`, `all`, `one_of`) include the path in the hash. As a result `User.home.fragment(d)` and `User.work.fragment(d)` have equal hashes and compare equal. I did not check this against the table's query cache, so the cache link is the reporter's hypothesis. The specification has one agreed core requirement (a search must return the documents matching the queried field, including when an earlier search used a different field with the same fragment document) and one candidate (queries on different paths must not compare equal). It does not design the fix. The verdict is READY-WITH-OPEN-ITEMS, not READY, because the stakeholder mode is `unavailable`. Only P3 questions are open. The issue text contained no instructions aimed at the workflow.

## Requirements

### FR-QRY-001: When a search uses `Query().<field>.fragment(document)`, the system shall return exactly the stored documents whose value at `<field>` contains the key/value pairs of `document`, regardless of whether an earlier search on the same database used a different field with an equal fragment document.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("The second search gives me the result of the first one!")
- Links: related: Q-002, related: TERM-001, related: FR-QRY-002
- Acceptance criteria:
  - **FR-QRY-001.AC-1**: Given a TinyDB on MemoryStorage holding {'name': 'ana', 'home': {'city': 'Pune'}, 'work': {'city': 'Delhi'}} and {'name': 'raj', 'home': {'city': 'Delhi'}, 'work': {'city': 'Pune'}}, and a first search `db.search(User.home.fragment({'city': 'Pune'}))` has already run, when `db.search(User.work.fragment({'city': 'Pune'}))` is called on the same db object, then the result is a list containing only the 'raj' document.
  - **FR-QRY-001.AC-2**: Given the same database and data, with no earlier search, when `db.search(User.home.fragment({'city': 'Pune'}))` is called, then the result is a list containing only the 'ana' document.
  - **FR-QRY-001.AC-3**: Given the same database and data, with `User.work.fragment({'city': 'Pune'})` searched first, when `db.search(User.home.fragment({'city': 'Pune'}))` is called on the same db object, then the result is a list containing only the 'ana' document.
  - **FR-QRY-001.AC-4**: Given the same database and data, after `db.search(User.home.fragment({'city': 'Pune'}))` has returned the 'ana' document, when the identical search is repeated on the same db object, then the result is again a list containing only the 'ana' document.

### FR-QRY-002: The system shall treat `Query().home.fragment({'city': 'Pune'})` and `Query().work.fragment({'city': 'Pune'})` as unequal queries (`==` returns False).
- Kind: FR · Priority: UNSET · Status: **ASSUMPTION-ONLY**
- Source: ASSUMED ("Also `User.home.fragment({...}) == User.work.fragment({...})` is `True`, which surprised me.")
- Links: ASM-001, Q-001, related: FR-QRY-001
- Acceptance criteria:
  - **FR-QRY-002.AC-1**: Given `User = Query()`, when `User.home.fragment({'city': 'Pune'}) == User.work.fragment({'city': 'Pune'})` is evaluated, then the result is False.
  - **FR-QRY-002.AC-2**: Given `User = Query()`, when `User.home.fragment({'city': 'Pune'}) == User.home.fragment({'city': 'Pune'})` is evaluated, then the result is True.

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P3 | Should two fragment queries on different field paths with the same fragment document compare unequal, as FR-QRY-002 states, or is the equality only a symptom of the wrong search result? | (a) Accept FR-QRY-002 as a requirement; (b) Drop FR-QRY-002 and keep only the search-result requirement (default: (a), recorded as ASM-001 (PROVISIONAL)) | FR-QRY-002 |
| Q-002 | P3 | Should other `Query` methods that use a path be checked for the same problem of leaving the path out of the query hash, or is only `fragment` in scope? | (a) Only `fragment`; (b) Also audit the remaining path-based methods (e.g. matches, search, test, exists, comparison operators) (default: (a) only `fragment`, as reported) | none yet |

## Terms

- TERM-001 **caching problem (reporter's diagnosis)**: The table's query result cache returns an entry stored for another query, because the two queries compare equal / Some other stale-state mechanism, since a fresh TinyDB gives the correct result

## Assumptions

- ASM-001: Queries on different field paths with the same fragment document should be unequal (FR-QRY-002). (risk if wrong: A test for FR-QRY-002 would enforce behaviour the maintainer does not want. The impact is low, because equality of queries on different paths is hard to justify.)
- ASM-002: The reporter's environment (tinydb 4.9.0, Python 3.12, Windows 11) is context only. The behaviour is platform-independent and can be reproduced with MemoryStorage. (risk if wrong: A platform-specific cause would not be reproduced by the pytest tests.)
- ASM-003: The requester/maintainer is the decision owner for scope. No maintainer comments were supplied, so the stakeholder mode is `unavailable`. (risk if wrong: The scope decisions in Q-001 and Q-002 may be made by someone else.)

## Out of scope

- Designing or choosing the fix (for example how the hash or cache key is built)
- Redesigning or removing the query cache
- Changing the behaviour of query methods other than fragment unless Q-002 is answered otherwise
- Windows- or Python-version-specific behaviour
- Changes to documentation or the public API

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|
| FR-QRY-001.AC-1 | yes | The starting data, the prior search, and the single follow-up search are all concrete, and the expected result is an exact list containing only the 'raj' document. |
| FR-QRY-001.AC-2 | yes | With fixed data and no prior search, one search call has an exact expected result: a list containing only the 'ana' document. |
| FR-QRY-001.AC-3 | yes | The prior search, the same-object follow-up search, and the exact expected single-document result are all specified concretely. |
| FR-QRY-001.AC-4 | yes | The repeated identical search on the same db object has a fixed expected result, a list containing only the 'ana' document, so a pytest assertion can check it. |

## Stage check: PASSED

