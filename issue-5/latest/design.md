# design.md

Make JSONStorage encode datetime.datetime/date via a json `default` hook as tagged dicts, and decode them via an `object_hook` on read. Only tinydb/storages.py changes; queries.py and MemoryStorage are deliberately left untouched.

## Approach

All changes are in tinydb/storages.py, where C4 and ADR-1 say serialisation lives. Add a module-level constant `_TYPE_KEY = '__tinydb_type__'` and `_VALUE_KEY = '__tinydb_value__'`, plus two private module-level functions:

- `_encode_temporal(obj)` is a `default` hook. For `datetime.datetime` (checked BEFORE `date`, since datetime subclasses date) it returns `{_TYPE_KEY: 'datetime', _VALUE_KEY: obj.isoformat()}`. For `datetime.date` it returns `{_TYPE_KEY: 'date', _VALUE_KEY: obj.isoformat()}`. Anything else raises TypeError, as json does by default. Naive datetimes give isoformat without an offset. Aware ones give `+05:30` or `+00:00`, so the offset is kept (ASM-003).
- `_decode_temporal(dct)` is an `object_hook`. Only a dict with exactly the two marker keys and a type of 'datetime' or 'date' is converted. For 'datetime' it calls `datetime.fromisoformat`. For 'date' it calls `date.fromisoformat`. Every other dict is returned unchanged. Plain strings are never parsed, so look-alike strings stay `str` (FR-JSON-004). The object_hook runs at every nesting depth, which gives the nested behaviour of ASM-001 for free.

`JSONStorage.write` passes `default` to `json.dumps`. If the user supplied `default` in kwargs, the hook tries the temporal encoding first and otherwise delegates to the user's function (ASM-004). Otherwise it uses `_encode_temporal`. The kwargs dict is copied, never mutated. `JSONStorage.read` uses `json.load(self._handle, object_hook=_decode_temporal)`. A user `cls` in kwargs is unaffected, because json calls `default` only for objects it cannot serialise natively.

`import datetime` is the only new import (standard library, C5/CON-001). pyproject.toml is not touched.

CON-003 (no Query change) is satisfied by omission. tinydb/queries.py and the `Query` class appear in no `files` entry. Queries already compare datetime and date objects natively, so once `read()` returns real objects after reopening, FR-JSON-005 works with no code change. CON-003's tests are verification-only. They compare the working tree to the base commit (`git diff <base> -- tinydb/queries.py` is empty) and compare `dir(Query)` with a snapshot taken from the base revision. Likewise MemoryStorage is not modified (CON-002).

## Files and symbols to change

| File | Change | Symbol | Kind | Symbol change | What |
|---|---|---|---|---|---|
| `tinydb/storages.py` | modify | `_TYPE_KEY` | constant | create | Marker key '__tinydb_type__' used in the tagged-dict encoding ('datetime' or 'date'). |
| `tinydb/storages.py` | modify | `_VALUE_KEY` | constant | create | Key '__tinydb_value__' holding the ISO 8601 text of the value. |
| `tinydb/storages.py` | modify | `_encode_temporal` | function | create | json `default` hook. Checks datetime before date and returns a tagged dict with isoformat() (offset kept for aware values). Raises TypeError for any other type. |
| `tinydb/storages.py` | modify | `_decode_temporal` | function | create | json `object_hook`. Converts a dict that has exactly the two marker keys and a known type via datetime.fromisoformat or date.fromisoformat. Returns every other dict unchanged. |
| `tinydb/storages.py` | modify | `JSONStorage.read` | method | modify | Call json.load(self._handle, object_hook=_decode_temporal). |
| `tinydb/storages.py` | modify | `JSONStorage.write` | method | modify | Pass a `default` to json.dumps. It is _encode_temporal, or a wrapper that tries it first and then delegates to a user-supplied `default` from self.kwargs. self.kwargs is copied, not mutated. |

## Acceptance criteria → code → test

| AC | Symbols | Test idea |
|---|---|---|
| FR-JSON-001.AC-1 | _encode_temporal, _decode_temporal, JSONStorage.write, JSONStorage.read | Insert {'when': datetime(2026,1,1,12,30,15,123456)} into a TinyDB on a tmp JSON file, close it, reopen, and assert all()[0]['when'] equals the original, type is datetime.datetime and tzinfo is None. |
| FR-JSON-001.AC-2 | _encode_temporal, JSONStorage.write | On a non-existent tmp path, insert a document with a datetime and assert no exception is raised. |
| FR-JSON-002.AC-1 | _encode_temporal, _decode_temporal, JSONStorage.write, JSONStorage.read | Round-trip {'day': date(2026,1,1)} and assert the value equals the original and type(value) is date, not datetime. |
| FR-JSON-003.AC-1 | _encode_temporal, _decode_temporal, JSONStorage.write, JSONStorage.read | Round-trip a datetime with tzinfo=timezone(timedelta(hours=5, minutes=30)); assert equality, utcoffset()==5:30 and tzinfo is not None. |
| FR-JSON-003.AC-2 | _encode_temporal, _decode_temporal | Round-trip a UTC-aware datetime; assert utcoffset()==timedelta(0) and equality. |
| FR-JSON-003.AC-3 | _encode_temporal, _decode_temporal | Insert a naive and a -08:00 aware datetime with the same wall time, reopen, and assert the first has tzinfo None and the second has utcoffset()==timedelta(hours=-8). |
| FR-JSON-004.AC-1 | _decode_temporal | Round-trip the strings '2026-01-01', '2026-01-01T12:00:00' and '2026-01-01T12:00:00+05:30'; assert each comes back as str with identical text. |
| FR-JSON-004.AC-2 | _encode_temporal, _decode_temporal | Store '2026-01-01' under 's' and date(2026,1,1) under 'd' in one document; after reopen assert type of 's' is str and type of 'd' is date. |
| FR-JSON-005.AC-1 | JSONStorage.read, _decode_temporal | Persist two datetimes, reopen, run db.search(Query().when < datetime(2026,1,1)) and assert exactly one result, the 2025 one. Query code is untouched; this works because read returns real datetimes. |
| FR-JSON-005.AC-2 | JSONStorage.read, _decode_temporal | Persist two dates, reopen, run db.search(Query().day >= date(2026,1,1)) and assert exactly one result, 2026-06-01. |
| FR-JSON-005.AC-3 | JSONStorage.read, _decode_temporal | Persist a UTC-aware datetime, reopen, run db.search(Query().when == the same aware datetime) and assert one match. |
| CON-001.AC-1 | tinydb/storages.py (imports only; pyproject.toml untouched) | Parse pyproject.toml with tomllib and assert [project] declares no runtime `dependencies`, equal to the base commit (empty). Optionally compare with `git show <base>:pyproject.toml`. |
| CON-001.AC-2 | tinydb/storages.py (new `import datetime`) | Use ast to collect top-level imported modules of tinydb/storages.py and assert each is in sys.stdlib_module_names or is 'tinydb'. |
| CON-002.AC-1 | MemoryStorage.read, MemoryStorage.write (unchanged) | On TinyDB(storage=MemoryStorage) insert {'when': datetime(2026,1,1)}, call all(), and assert the value equals datetime(2026,1,1) and is the same datetime type. |
| CON-002.AC-2 | MemoryStorage (unchanged) | With ast, compare the source segment of class MemoryStorage in the working tree with the one from `git show <base>:tinydb/storages.py` and assert they are identical. |
| CON-003.AC-1 | tinydb/queries.py (unchanged; not listed in files), Query (unchanged) | Run `git diff <base-commit> -- tinydb/queries.py` (or compare the file bytes with `git show <base>:tinydb/queries.py`) and assert the diff is empty. The base is the merge base with main. |
| CON-003.AC-2 | Query (unchanged), tinydb/queries.py (unchanged; not listed in files) | Load Query from `git show <base>:tinydb/queries.py` into a temporary module, or compare against a hard-coded snapshot of the base public names. Assert set(dir(Query)) is identical to the current set(dir(tinydb.queries.Query)). |

## Architecture constraints (ARCHITECTURE.md)

- C1: The Storage interface is unchanged. read() still returns None for an empty file and write() still takes the whole dict. The hooks sit inside JSONStorage's existing read and write.
- C2: No query operation is added or changed, so no new hash is needed. queries.py is not touched (CON-003). Comparisons use Python's native datetime and date operators on values that read() now returns as real objects.
- C3: Table and _update_table are not modified. The conversion happens only inside the storage's write and read, so the write path and cache invalidation are unchanged.
- C4: storages.py imports only the standard library (a new `import datetime`) and no other tinydb module. queries.py is unchanged.
- C5: Only the stdlib `datetime` and `json` modules are used. pyproject.toml is not edited, so no runtime dependency is added.

## Alternatives considered

- Parse ISO-looking strings back into dates on read: This violates FR-JSON-004 and the maintainer's decision 3: look-alike strings must stay strings.
- Add datetime handling to Query (new operators or coercion of strings): CON-003 forbids any change to Query or queries.py. It is also unnecessary once real datetime objects are returned on read.
- Add a middleware, e.g. DateTimeMiddleware, that converts values: This would force users to opt in, so datetimes would still fail with plain JSONStorage (FR-JSON-001.AC-2). It would also need a tree walk on every read and write, which is more code than a json hook.
- Handle datetimes in Table._update_table or Table.insert: This breaks C3/C4 and the ADR that serialisation lives only in storages. It would also change MemoryStorage behaviour (CON-002).
- Store a bare marker string prefix such as 'dt:2026-...': A user string with the same prefix would be decoded wrongly, which breaks FR-JSON-004. A tagged dict only collides with a dict that has exactly the marker keys (documented limitation, ASM-002).

## Risks

- Collision limitation (Q-002/ASM-002): a user dict with exactly the keys '__tinydb_type__' and '__tinydb_value__' and a known type will be decoded as a date or datetime. The decoder is strict, converting only an exact two-key match with a known type and a parseable value, to keep this rare. If fromisoformat raises on a malformed value, the dict should be left unchanged, so wrap it in try/except ValueError and return the dict.
- Aware datetimes come back with datetime.timezone fixed offsets, not the original tzinfo class such as ZoneInfo (Q-004/ASM-003). The instant and offset are equal, but DST semantics are lost.
- datetime subclasses (e.g. pandas.Timestamp) are encoded as plain datetime and come back as datetime (Q-003). time and timedelta are unchanged and still raise TypeError.
- A user-supplied `default` in JSONStorage kwargs is now wrapped. Temporal values are handled first and everything else goes to the user's function. Behaviour for non-date values stays the same (ASM-004). Existing files with no marker dicts load identically, but json.load now always runs with an object_hook, which costs a little speed on large files.
- A datetime used as a dict key is still unsupported (json rejects non-string keys); this is outside the spec.
- Python version: date.fromisoformat and datetime.fromisoformat need Python 3.7+ for the formats isoformat() emits, which is fine here because the code already uses `dict[str, ...]` generics (3.9+). The spec itself looks consistent; CON-003 and CON-002 are verification-only and need no source change.

## Stage check: PASSED

