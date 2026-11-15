# pr.md

- PR: https://github.com/iDheer/tinydb/pull/14
- Head: `d291903fb47554898b5027e1c86e6247b19f3461`
- CI: success https://github.com/iDheer/tinydb/actions/runs/43717773407

---

Closes #2

**autose** generated this pull request for issue #2 (one_of() with a generator only matches some of the documents).
A separate reviewer agent will post a review; a person decides whether to merge.

## What changed

Fix Query.one_of so a generator (any one-shot iterator) is materialised into a list once, when the query is built, so every document is tested against the full set of values and the query is reusable.

In Query.one_of, an Iterator argument (generator, map, filter, iter) is now turned into a list once at query construction. Both the membership test and the hash use that list, so generators no longer get exhausted, queries can be reused, and an empty generator matches nothing. Lists and other non-iterator inputs are untouched. I also changed the type hint to Iterable[Any], imported Iterable and Iterator from collections.abc, and updated the docstring. All 228 existing tests pass and mypy is clean. I did not write tests for the new behaviour.

## Acceptance criteria covered

- FR-QUERY-001.AC-1: Given a TinyDB with MemoryStorage holding [{'tag':'a'},{'tag':'b'},{'tag':'a'},{'tag':'c'}] and allowed = (t for t in ['a','b']), when db.search(Query().tag.one_of(allowed)) is called, then the result equals [{'tag':'a'},{'tag':'b'},{'tag':'a'}].
- FR-QUERY-001.AC-2: Given q = Query().key1.one_of(v for v in ['value 1','value 2']), when q is called directly on {'key1':'value 1'}, then {'key1':'value 2'}, then {'key1':'value 1'}, in that order, then all three calls return True.
- FR-QUERY-001.AC-3: Given q = Query().key1.one_of(v for v in ['value 1','value 2']), when q is called on {'key1':'value 3'}, then it returns False.
- FR-QUERY-001.AC-4: Given documents [{'tag':'b'},{'tag':'a'},{'tag':'a'}] and a generator yielding 'a' then 'b', when db.search(Query().tag.one_of(generator)) is called, then the result equals [{'tag':'b'},{'tag':'a'},{'tag':'a'}] (order of the generated values does not affect which documents match).
- FR-QUERY-002.AC-1: Given q = Query().key1.one_of(['value 1','value 2']), when q is called on {'key1':'value 1'}, {'key1':'value 2'} and {'key1':'value 3'}, then it returns True, True and False respectively.
- FR-QUERY-002.AC-2: Given a TinyDB with MemoryStorage holding [{'tag':'a'},{'tag':'b'},{'tag':'a'},{'tag':'c'}], when db.search(Query().tag.one_of(['a','b'])) is called, then the result equals [{'tag':'a'},{'tag':'b'},{'tag':'a'}].
- FR-QUERY-003.AC-1: Given a TinyDB holding [{'tag':'a'},{'tag':'b'},{'tag':'c'}] and q = Query().tag.one_of(t for t in ['a','b']), when db.search(q) is called twice, then both results equal [{'tag':'a'},{'tag':'b'}] (to be confirmed by Q-001).
- FR-QUERY-004.AC-1: Given a document {'tag':'a'} and q = Query().tag.one_of(t for t in []), when q is called on the document, then it returns False.

## Tests

- Full suite: 234 passed, 0 failed
- New tests: `tests/test_autose_issue_2.py` (6 tests)

## Run artifacts

- [spec.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-2/run-43717567536-1/spec.md)
- [design.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-2/run-43717567536-1/design.md)
- [diff.patch](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-2/run-43717567536-1/diff.patch)
- [test_report.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-2/run-43717567536-1/test_report.md)
- [Actions run](https://github.com/iDheer/tinydb/actions/runs/43717567536)
