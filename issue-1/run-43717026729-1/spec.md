# spec.md: fragment() queries on different nested fields must return results for their own field

- Issue: #1 https://github.com/iDheer/tinydb/issues/1
- Verdict (A1 skill): **READY-WITH-OPEN-ITEMS**, stakeholder mode: unavailable

Precise bug report. In the repo, Query.fragment() builds its hash value as ('fragment', freeze(document)) without the query path (tinydb/queries.py:497-501), whereas other path-based queries such as one_of include self._path. Two fragment queries on different paths with the same fragment therefore compare equal and share a Table query-cache entry, so the second search returns the first one's cached result. The spec has one core requirement (FR-QRY-001, READY: search by fragment on a nested field returns the documents matching that field, regardless of earlier searches). It also has one candidate requirement (FR-QRY-002, ASSUMED: queries for different paths compare unequal), which is not core. The acceptance criteria now give the full contents of both documents and the exact expected result lists. Stakeholder mode is unavailable, so only P3 questions remain, which gives READY-WITH-OPEN-ITEMS. The issue contains no instructions aimed at the workflow.

## Requirements

### FR-QRY-001: When db.search() is called with a fragment query on a nested field path, the system shall return exactly the documents whose value at that path contains the given fragment, regardless of which other fragment queries on other paths were run earlier on the same TinyDB instance.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("expected [raj], but I get [ana] again")
- Links: TERM-001, related: Q-002
- Acceptance criteria:
  - **FR-QRY-001.AC-1**: Given a TinyDB(storage=MemoryStorage) containing exactly two documents, A = {'name': 'ana', 'home': {'city': 'Pune'}, 'work': {'city': 'Delhi'}} and B = {'name': 'raj', 'home': {'city': 'Delhi'}, 'work': {'city': 'Pune'}}, and db.search(User.home.fragment({'city': 'Pune'})) has already been executed once on this instance, when db.search(User.work.fragment({'city': 'Pune'})) is executed on the same instance, then the result is a list with exactly one document equal to B ({'name': 'raj', 'home': {'city': 'Delhi'}, 'work': {'city': 'Pune'}}), and A is not in it.
  - **FR-QRY-001.AC-2**: Given a TinyDB(storage=MemoryStorage) containing exactly the two documents A = {'name': 'ana', 'home': {'city': 'Pune'}, 'work': {'city': 'Delhi'}} and B = {'name': 'raj', 'home': {'city': 'Delhi'}, 'work': {'city': 'Pune'}}, when db.search(User.home.fragment({'city': 'Pune'})) is executed as the first search on that instance, then the result is a list with exactly one document equal to A ({'name': 'ana', 'home': {'city': 'Pune'}, 'work': {'city': 'Delhi'}}).
  - **FR-QRY-001.AC-3**: Given a TinyDB(storage=MemoryStorage) containing exactly the two documents A and B of AC-1, and db.search(User.work.fragment({'city': 'Pune'})) has already been executed once on this instance (returning [B]), when db.search(User.home.fragment({'city': 'Pune'})) is executed on the same instance, then the result is a list with exactly one document equal to A, and B is not in it.
  - **FR-QRY-001.AC-4**: Given the same instance and documents A and B as AC-1, after the home search and then the work search have both been executed, when db.search(User.home.fragment({'city': 'Pune'})) is executed a second time, then the result is a list with exactly one document equal to A.

### FR-QRY-002: If the reporter's surprise at equality is read as an expectation (Q-001), the system shall evaluate a fragment query on one path as not equal to a fragment query with the same fragment on a different path.
- Kind: FR · Priority: UNSET · Status: **ASSUMPTION-ONLY**
- Source: ASSUMED ("Also `User.home.fragment({...}) == User.work.fragment({...})` is `True`, which surprised me.")
- Links: ASM-001, Q-001, related: FR-QRY-001
- Acceptance criteria:
  - **FR-QRY-002.AC-1**: Given User = Query(), when the expression User.home.fragment({'city': 'Pune'}) == User.work.fragment({'city': 'Pune'}) is evaluated, then the result is False.
  - **FR-QRY-002.AC-2**: Given User = Query(), when the expression User.home.fragment({'city': 'Pune'}) == User.home.fragment({'city': 'Pune'}) is evaluated, then the result is True.

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P3 | Should two fragment queries with the same fragment but different paths compare unequal (== returns False), as the reporter's surprise at True suggests? | Yes, they must compare unequal; No requirement on equality; only search results matter (default: Yes, they must compare unequal (recorded as ASM-001, PROVISIONAL)) | FR-QRY-002 |
| Q-002 | P3 | Is the fix limited to Query.fragment(), or should other query methods be checked for the same problem of two different paths sharing one query identity? | fragment() only; Audit all Query methods that take a path (default: fragment() only, with no requirement for other methods (recorded as ASM-002, PROVISIONAL)) | none yet |

## Terms

- TERM-001 **"it looks like some caching problem" (and "fresh TinyDB")**: The reporter's hypothesis about the cause (the Table query cache returning an earlier result). It is a diagnosis, not a requirement, and no requirement depends on it. / A request that caching behaviour change, for example removing or disabling the query cache. Nothing in the issue says this, so it is not recorded as a requirement.

## Assumptions

- ASM-001: The reporter's surprise that the two fragment queries compare equal means the expected result is False (not equal) for different paths. The requester or maintainer decides. (risk if wrong: FR-QRY-002 would be rejected or reworded. Core behaviour FR-QRY-001 is unaffected.)
- ASM-002: Only fragment() is in scope for this issue. Other Query methods are reported to behave correctly and are not required to change. (risk if wrong: A similar fault in another query method would stay unreported and untested.)

## Out of scope

- Choosing or designing the fix (for example how the query hash is built, or whether the cache is changed).
- Behaviour of other Query methods (one_of, ==, etc.) unless a maintainer answers Q-002 otherwise.
- Platform-specific behaviour: the Windows 11 and Python 3.12 details in the issue are context only, and the bug does not look platform-dependent.
- Changes to the query cache policy, such as disabling the cache or changing its size.

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|
| FR-QRY-001.AC-1 | yes | The starting documents, the prior search, and the second search are all concrete, and the expected result is an exact one-item list equal to B with A absent. |
| FR-QRY-001.AC-2 | yes | A first-run search on a known two-document database has a concrete expected result, a one-item list equal to A. |
| FR-QRY-001.AC-3 | yes | The prior work search, the home search, and the expected one-item list containing A without B are all specified exactly enough to assert. |
| FR-QRY-001.AC-4 | yes | After a fixed sequence of home and work searches, a repeated home search has a concrete expected result, a one-item list equal to A. |

## Stage check: PASSED

