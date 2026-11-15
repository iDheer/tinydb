# pr.md

- PR: https://github.com/iDheer/tinydb/pull/12
- Head: `1ff2b1830c1f6050c5fbf09cff07a91d50a3f861`
- CI: success https://github.com/iDheer/tinydb/actions/runs/43717273822

---

Closes #1

**autose** generated this pull request for issue #1 (Searching with fragment() on a nested field returns the results of a different field).
A separate reviewer agent will post a review; a person decides whether to merge.

## What changed

Include the query path (self._path) in the hash value built by Query.fragment() so fragment queries on different paths no longer compare equal or share a Table query-cache entry.

Query.fragment() now builds its hash as ('fragment', self._path, freeze(document)), like one_of. Fragment queries on different paths no longer compare equal or share a Table query-cache entry. All 228 existing tests pass and mypy is clean. I did not add tests for the new behaviour.

## Acceptance criteria covered

- FR-QRY-001.AC-1: Given a TinyDB(storage=MemoryStorage) containing exactly two documents, A = {'name': 'ana', 'home': {'city': 'Pune'}, 'work': {'city': 'Delhi'}} and B = {'name': 'raj', 'home': {'city': 'Delhi'}, 'work': {'city': 'Pune'}}, and db.search(User.home.fragment({'city': 'Pune'})) has already been executed once on this instance, when db.search(User.work.fragment({'city': 'Pune'})) is executed on the same instance, then the result is a list with exactly one document equal to B ({'name': 'raj', 'home': {'city': 'Delhi'}, 'work': {'city': 'Pune'}}), and A is not in it.
- FR-QRY-001.AC-2: Given a TinyDB(storage=MemoryStorage) containing exactly the two documents A = {'name': 'ana', 'home': {'city': 'Pune'}, 'work': {'city': 'Delhi'}} and B = {'name': 'raj', 'home': {'city': 'Delhi'}, 'work': {'city': 'Pune'}}, when db.search(User.home.fragment({'city': 'Pune'})) is executed as the first search on that instance, then the result is a list with exactly one document equal to A ({'name': 'ana', 'home': {'city': 'Pune'}, 'work': {'city': 'Delhi'}}).
- FR-QRY-001.AC-3: Given a TinyDB(storage=MemoryStorage) containing exactly the two documents A and B of AC-1, and db.search(User.work.fragment({'city': 'Pune'})) has already been executed once on this instance (returning [B]), when db.search(User.home.fragment({'city': 'Pune'})) is executed on the same instance, then the result is a list with exactly one document equal to A, and B is not in it.
- FR-QRY-001.AC-4: Given the same instance and documents A and B as AC-1, after the home search and then the work search have both been executed, when db.search(User.home.fragment({'city': 'Pune'})) is executed a second time, then the result is a list with exactly one document equal to A.
- FR-QRY-002.AC-1: Given User = Query(), when the expression User.home.fragment({'city': 'Pune'}) == User.work.fragment({'city': 'Pune'}) is evaluated, then the result is False.
- FR-QRY-002.AC-2: Given User = Query(), when the expression User.home.fragment({'city': 'Pune'}) == User.home.fragment({'city': 'Pune'}) is evaluated, then the result is True.

## Tests

- Full suite: 232 passed, 0 failed
- New tests: `tests/test_autose_issue_1.py` (4 tests)

## Run artifacts

- [spec.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-1/run-43717026729-1/spec.md)
- [design.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-1/run-43717026729-1/design.md)
- [diff.patch](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-1/run-43717026729-1/diff.patch)
- [test_report.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-1/run-43717026729-1/test_report.md)
- [Actions run](https://github.com/iDheer/tinydb/actions/runs/43717026729)
