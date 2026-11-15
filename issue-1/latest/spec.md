# spec.md: fragment() on a nested query path must test that path, not another path's result

- Issue: #1 https://github.com/iDheer/tinydb/issues/1
- Verdict (A1 skill): **READY-WITH-OPEN-ITEMS**, stakeholder mode: unavailable

Issue #1 is a precise bug report. `Query.fragment()` is built with a hash of `('fragment', freeze(document))` only (tinydb/queries.py:497-501). The query path is not part of it, although `_generate_test` does resolve the path at run time. As a result `User.home.fragment(x)` and `User.work.fragment(x)` hash and compare equal. This matches the reporter's observation that the second search returns the first search's result and that the two queries compare `True`. One core requirement (correct results per path) is READY. The equality expectation is only implied by "surprised me", so it is recorded as a candidate with a P3 question. No stakeholder or maintainer comments are available, so the verdict cannot be READY. The issue text contained no instructions aimed at the agent. No tools were used for evidence because there are no tool-answerable questions: the issue names no external standard.

## Requirements

### FR-QFRAG-001: When a database is searched with a fragment query on a nested field path, the system shall return exactly the documents whose value at that path contains the given fragment, regardless of any earlier search with the same fragment on a different path in the same TinyDB instance.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("print(db.search(User.work.fragment({'city': 'Pune'})))  # expected [raj], but I get [ana] again")
- Links: related: Q-001, related: TERM-001, related: RSK-001
- Acceptance criteria:
  - **FR-QFRAG-001.AC-1**: Given a TinyDB on MemoryStorage with documents {'name':'ana','home':{'city':'Pune'},'work':{'city':'Delhi'}} and {'name':'raj','home':{'city':'Delhi'},'work':{'city':'Pune'}}, and db.search(User.home.fragment({'city':'Pune'})) has already been executed on it, when db.search(User.work.fragment({'city':'Pune'})) is executed on the same TinyDB instance, then the result is a list containing only the document with name 'raj'.
  - **FR-QFRAG-001.AC-2**: Given the same two documents in a freshly created TinyDB on MemoryStorage and no earlier search, when db.search(User.work.fragment({'city':'Pune'})) is executed, then the result is a list containing only the document with name 'raj'.
  - **FR-QFRAG-001.AC-3**: Given the same two documents, and db.search(User.work.fragment({'city':'Pune'})) has already been executed on the same instance, when db.search(User.home.fragment({'city':'Pune'})) is executed, then the result is a list containing only the document with name 'ana'.

### FR-QFRAG-002: Candidate (not agreed): two fragment queries built on different field paths with the same fragment document shall not compare equal.
- Kind: FR · Priority: UNSET · Status: **ASSUMPTION-ONLY**
- Source: ASSUMED ("Also `User.home.fragment({...}) == User.work.fragment({...})` is `True`, which surprised me.")
- Links: ASM-001, related: Q-001
- Acceptance criteria:
  - **FR-QFRAG-002.AC-1**: Given User = Query(), when User.home.fragment({'city': 'Pune'}) == User.work.fragment({'city': 'Pune'}) is evaluated, then the result is False.
  - **FR-QFRAG-002.AC-2**: Given User = Query(), when User.home.fragment({'city': 'Pune'}) == User.home.fragment({'city': 'Pune'}) is evaluated, then the result is True.

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P3 | Should two fragment queries on different paths with the same fragment document also be unequal (== False) and have different hashes, as a requirement in its own right and not only as a side effect of correct search results? | (a) Yes, queries with different paths must be unequal; (b) No, only search results must be correct (default: (a), recorded as ASM-001 (PROVISIONAL)) | FR-QFRAG-002 |
| Q-002 | P3 | Is the same-path-different-result problem expected to be checked and fixed for other query methods and for deeper or map() paths, or only for fragment()? | (a) fragment() only; (b) also audit other Query test methods and deeper paths (default: (a) fragment() only. Deeper paths via fragment() are covered implicitly by FR-QFRAG-001's 'nested field path'.) | none yet |

## Terms

- TERM-001 **caching problem**: The query-result cache of the table returns a stored result because it considers the two queries identical (consistent with the equal queries the reporter observed). / The cache is stale across searches for some other reason (the reporter's guess, not a stated requirement). Either reading only describes the cause; the required behaviour is in FR-QFRAG-001.
- TERM-002 **nested field**: A dict-valued field reached via attribute access, such as User.home. This is the case in the issue example. / A deeper path, such as User.a.b.c, or a path through Query()['key'] or a map() step. The issue shows only one level, so deeper paths are not specified.

## Assumptions

- ASM-001: Equal-looking queries on different paths should compare unequal and hash differently (the reporter's surprise is read as an expectation). (risk if wrong: A needless equality or hash requirement would be added. This is low impact because the search-result requirement is independent.)
- ASM-002: The maintainer of iDheer/tinydb is the decision owner for scope questions, and the reporter is the requester. The issue-time stakeholder mode is unavailable. (risk if wrong: Q-001 and Q-002 may go to the wrong person. No core requirement depends on it.)
- ASM-003: Python 3.12, Windows 11 and tinydb 4.9.0 are context only. The behaviour is expected to be platform independent, and the repository code shows the path missing from the fragment hash regardless of platform. (risk if wrong: If the failure were platform-specific, the acceptance tests would pass on Linux without reproducing the reporter's problem.)

## Out of scope

- The design of the fix, including how the query hash or cache key is built
- Changes to query result caching in general, or to the query cache size
- Root-level fragment queries such as Query().fragment({...}) with an empty path, which are existing behaviour not mentioned in the issue
- Other Query methods such as all, one_of and test, unless Q-002 is answered otherwise
- Opening a fresh TinyDB between searches as a workaround

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|
| FR-QFRAG-001.AC-1 | yes | Concrete starting state (two named documents, MemoryStorage, prior search on the same instance), a single search action, and an explicit expected result (a list containing only the document named 'raj') that a pytest assertion can check. |
| FR-QFRAG-001.AC-2 | yes | Concrete fresh TinyDB with two named documents and no prior search, one search action, and an explicit expected result (a list containing only 'raj') that can be asserted directly. |
| FR-QFRAG-001.AC-3 | yes | Concrete state with a prior search on the same instance, one follow-up search, and an explicit expected result (a list containing only 'ana') that is unambiguous and assertable. |

## Stage check: PASSED

