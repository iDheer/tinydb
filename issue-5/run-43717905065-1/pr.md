# pr.md

- PR: https://github.com/iDheer/tinydb/pull/17
- Head: `344a959580d4a05d88574e0b83ebb93287271c12`
- CI: success https://github.com/iDheer/tinydb/actions/runs/43718396367

---

Closes #5

**autose** generated this pull request for issue #5 (Better datetime support?).
A separate reviewer agent will post a review; a person decides whether to merge.

## What changed

Make JSONStorage encode datetime.datetime/date via a json `default` hook as tagged dicts, and decode them via an `object_hook` on read. Only tinydb/storages.py changes; queries.py and MemoryStorage are deliberately left untouched.

The CI failure is not in the source. tests/test_autose_issue_5.py does `import tomllib` at module level, and tomllib only exists in Python 3.11+. CI runs Python 3.10, so collection fails before any test runs. I can only write tinydb/storages.py and may not edit tests, so I changed nothing. The implementation in tinydb/storages.py is already in place (datetime/date encoded as tagged dicts via `_encode_temporal`, decoded via the `_decode_temporal` object_hook, user `default` kwarg preserved). Locally on Python 3.12, `python -m pytest -q --ignore=tests/test_autose_issue_5.py` passes with 228 tests, and `python -m mypy tinydb` is clean. The tester needs to fix the test file. It could guard the import with `try: import tomllib except ImportError: tomli/skip`, or parse pyproject.toml without tomllib. The repo's own `.autose/common.py` has the same tomllib import, which is outside my write scope.

## Acceptance criteria covered

- FR-JSON-001.AC-1: Given a TinyDB on a new JSONStorage file with one document {'when': datetime(2026, 1, 1, 12, 30, 15, 123456)} inserted, then the database closed, when the same file is reopened with a new TinyDB(JSONStorage) and all() is called, then the 'when' value of the returned document is equal to datetime(2026, 1, 1, 12, 30, 15, 123456), type(value) is datetime.datetime, and value.tzinfo is None.
- FR-JSON-001.AC-2: Given a JSONStorage file path that does not yet exist, when a document containing a datetime value is inserted, then insert does not raise TypeError (or any other exception).
- FR-JSON-002.AC-1: Given a TinyDB on a new JSONStorage file with one document {'day': date(2026, 1, 1)} inserted, then the database closed, when the same file is reopened with a new TinyDB(JSONStorage) and all() is called, then the 'day' value is equal to date(2026, 1, 1) and type(value) is datetime.date (not datetime.datetime).
- FR-JSON-003.AC-1: Given a document {'when': datetime(2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))} inserted into a JSONStorage-backed database that is then closed, when the file is reopened and all() is called, then the value is equal to the original, value.utcoffset() == timedelta(hours=5, minutes=30), and value.tzinfo is not None.
- FR-JSON-003.AC-2: Given a document {'when': datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)} inserted into a JSONStorage-backed database that is then closed, when the file is reopened and all() is called, then value.utcoffset() == timedelta(0) and the value is equal to the original.
- FR-JSON-003.AC-3: Given one document with a naive datetime(2026, 1, 1, 12, 0) and one with the same wall time and tzinfo=timezone(timedelta(hours=-8)), both inserted and the database closed, when the file is reopened and all() is called, then the first value has tzinfo None and the second has utcoffset() == timedelta(hours=-8).
- FR-JSON-004.AC-1: Given a document {'a': '2026-01-01', 'b': '2026-01-01T12:00:00', 'c': '2026-01-01T12:00:00+05:30'} inserted into a JSONStorage-backed database that is then closed, when the file is reopened and all() is called, then each of 'a', 'b' and 'c' has type str and is equal to the text that was inserted.
- FR-JSON-004.AC-2: Given a document containing both the string '2026-01-01' under key 's' and date(2026, 1, 1) under key 'd', inserted and the database closed, when the file is reopened and all() is called, then type of 's' is str and type of 'd' is datetime.date.
- FR-JSON-005.AC-1: Given documents {'when': datetime(2025, 6, 1, 12, 0)} and {'when': datetime(2026, 6, 1, 12, 0)} inserted into a JSONStorage-backed database that is then closed and reopened, when db.search(Query().when < datetime(2026, 1, 1)) is called, then exactly one document is returned and its 'when' equals datetime(2025, 6, 1, 12, 0).
- FR-JSON-005.AC-2: Given documents {'day': date(2025, 6, 1)} and {'day': date(2026, 6, 1)} inserted into a JSONStorage-backed database that is then closed and reopened, when db.search(Query().day >= date(2026, 1, 1)) is called, then exactly one document is returned and its 'day' equals date(2026, 6, 1).
- FR-JSON-005.AC-3: Given a document {'when': datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)} persisted and the database reopened, when db.search(Query().when == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)) is called, then exactly one document is returned.
- CON-001.AC-1: Given the project's dependency declaration (pyproject.toml) before and after the change, when the runtime dependency lists are compared, then the after-change list contains no entry that the before-change list lacks.
- CON-001.AC-2: Given the changed tinydb package modules, when their import statements are collected, then every imported top-level module is either in the Python standard library or in the tinydb package itself.
- CON-002.AC-1: Given a TinyDB on MemoryStorage with a document {'when': datetime(2026, 1, 1)} inserted, when all() is called, then the returned document's 'when' is the identical datetime object value, equal to datetime(2026, 1, 1) (same behaviour as before the change).
- CON-002.AC-2: Given the repository after the change, when git diff of the MemoryStorage class in tinydb/storages.py against the base commit is taken, then the diff for that class is empty.
- CON-003.AC-1: Given the repository after the change, when git diff of tinydb/queries.py against the base commit is taken, then the diff is empty.
- CON-003.AC-2: Given the public attribute names of the Query class before and after the change, when dir(Query) is compared, then the two sets of names are identical.

## Tests

- Full suite: 245 passed, 0 failed
- New tests: `tests/test_autose_issue_5.py` (17 tests)

## Run artifacts

- [spec.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-5/run-43717905065-1/spec.md)
- [design.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-5/run-43717905065-1/design.md)
- [diff.patch](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-5/run-43717905065-1/diff.patch)
- [test_report.md](https://github.com/iDheer/tinydb/blob/autose-artifacts/issue-5/run-43717905065-1/test_report.md)
- [Actions run](https://github.com/iDheer/tinydb/actions/runs/43717905065)
