# pr.md

- PR: https://github.com/iDheer/tinydb/pull/15
- Head: `ac8496bad1b7423333f6da3bedd9eab466f39248`
- CI: success https://github.com/iDheer/tinydb/actions/runs/43717814573

---

Closes #3

**autose** generated this pull request for issue #3 (Feature request: limit the number of results returned by search()).
A separate reviewer agent will post a review; a person decides whether to merge.

## What changed

Add an optional keyword-only `limit` parameter to `Table.search()` (reached by `TinyDB.search` via `__getattr__`, so no change to database.py). The scan stops after N matches, the result is the first N in table order, and a truncated result is never written to the query cache.

Added keyword-only `limit: Optional[int] = None` to Table.search in tinydb/table.py. None means no limit and 0 returns []. A negative value raises ValueError, and a non-int or bool raises TypeError. A cache hit returns cached_results[:limit]. On a cache miss the scan stops after `limit` matches. A truncated result is never cached, so a later unlimited search still returns every match. The docstring is updated. The 228 existing tests pass and mypy is clean. I did not run any new tests for the limit behaviour, since tests are the tester's job.

## Acceptance criteria covered

- FR-SEARCH-001.AC-1: Given a table with 25 documents of which 15 match Query().level == 'error', when table.search(Query().level == 'error', limit=10) is called, then the returned list has length 10 and every element satisfies level == 'error'.
- FR-SEARCH-001.AC-2: Given a table with 3 documents matching Query().level == 'error', when table.search(Query().level == 'error', limit=10) is called, then the returned list has length 3 and contains all 3 matching documents.
- FR-SEARCH-001.AC-3: Given a table in which exactly 10 documents match the query, when search(query, limit=10) is called, then the returned list has length 10.
- FR-SEARCH-001.AC-4: Given a TinyDB instance (default table) with 15 matching documents, when db.search(Query().level == 'error', limit=10) is called, then the returned list has length 10 and no exception is raised.
- FR-SEARCH-001.AC-5: Given a table with 15 matching documents where search(query) with no limit has already been called once, so the result is cached, when search(query, limit=10) is called with the same query, then the returned list has length 10.
- FR-SEARCH-002.AC-1: Given a table with documents inserted in the order [{'n':1,'level':'error'}, {'n':2,'level':'info'}, {'n':3,'level':'error'}, {'n':4,'level':'error'}], when search(Query().level == 'error', limit=2) is called, then the result equals the first 2 elements of search(Query().level == 'error') called without limit, i.e. the documents with n == 1 and n == 3, in that order.
- FR-SEARCH-002.AC-2: Given a table with 12 matching documents, when search(query, limit=5) is called, then the doc_ids of the result equal the first 5 doc_ids of search(query) without limit, in the same order.
- FR-SEARCH-003.AC-1: Given a table with 15 matching documents, when search(query) is called without limit, then the returned list has length 15 and contains every matching document in insertion order.
- FR-SEARCH-003.AC-2: Given a table where search(query) is called twice without limit, when the second call returns, then the result equals the first result and is a new list object (mutating it does not change a third call's result length).
- FR-SEARCH-003.AC-3: Given a table with no matching documents, when search(query) is called without limit, then the returned value is an empty list.
- FR-SEARCH-003.AC-4: Given the existing tinydb test-suite, when it is run unchanged, then all previously passing tests still pass.

## Tests

- Full suite: 239 passed, 0 failed
- New tests: `tests/test_autose_issue_3.py` (11 tests)

## Run artifacts

- [spec.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-3/run-43717570478-1/spec.md)
- [design.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-3/run-43717570478-1/design.md)
- [diff.patch](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-3/run-43717570478-1/diff.patch)
- [test_report.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-3/run-43717570478-1/test_report.md)
- [Actions run](https://github.com/iDheer/tinydb/actions/runs/43717570478)
