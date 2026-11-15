# spec.md: JSONStorage round-trip persistence of datetime and date values

- Issue: #5 https://github.com/iDheer/tinydb/issues/5
- Verdict (A1 skill): **READY**, stakeholder mode: unavailable

The issue (SRC-1) is vague ("Better datetime support?"), but the maintainer's decisions (SRC-2) narrow it to one scope: JSONStorage must persist datetime.datetime and datetime.date values so they come back with the same type and value after reopening. Naive datetimes stay naive, aware ones keep their UTC offset, look-alike strings stay strings, no new dependencies, no MemoryStorage change, and no Query change. Checked against the code: JSONStorage.write calls json.dumps(data, **self.kwargs) with no default hook (tinydb/storages.py:147), so a datetime inside a document currently cannot be serialized. JSONStorage.read returns json.load output unchanged (tinydb/storages.py:140). Five FRs and three CONs are CONFIRMED by the maintainer and READY. Four P3 questions remain (nested containers, other date/time types, tzinfo identity, marker collision), each with a proposed default. They block no core requirement. The issue's vague goals ("better", "out of the box", "painful") are not requirements. They are narrowed by SRC-2 decisions 1-5 and recorded as terms. No tool calls were made (no tool-answerable questions). The issue text contained no instructions aimed at the agent.

## Requirements

### FR-JSON-001: The system shall persist a naive datetime.datetime value stored in a document by JSONStorage so that, after the database is reopened, the value read back is a datetime.datetime that is equal to the original and has no tzinfo.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: CONFIRMED ("`datetime.datetime` and `datetime.date` values inside documents must be written to the JSON file and come back as the same type and the same value when the database is reopened")
- Links: related: Q-001, related: Q-004, related: ASM-001, CON-002
- Acceptance criteria:
  - **FR-JSON-001.AC-1**: Given a TinyDB on a new JSONStorage file with one document {'when': datetime(2026, 1, 1, 12, 30, 15, 123456)} inserted, then the database closed, when the same file is reopened with a new TinyDB(JSONStorage) and all() is called, then the 'when' value of the returned document is equal to datetime(2026, 1, 1, 12, 30, 15, 123456), type(value) is datetime.datetime, and value.tzinfo is None.
  - **FR-JSON-001.AC-2**: Given a JSONStorage file path that does not yet exist, when a document containing a datetime value is inserted, then insert does not raise TypeError (or any other exception).

### FR-JSON-002: The system shall persist a datetime.date value stored in a document by JSONStorage so that, after the database is reopened, the value read back is a datetime.date (and not a datetime.datetime) that is equal to the original.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: CONFIRMED ("`datetime.datetime` and `datetime.date` values inside documents must be written to the JSON file and come back as the same type and the same value when the database is reopened")
- Links: related: Q-001, related: Q-003
- Acceptance criteria:
  - **FR-JSON-002.AC-1**: Given a TinyDB on a new JSONStorage file with one document {'day': date(2026, 1, 1)} inserted, then the database closed, when the same file is reopened with a new TinyDB(JSONStorage) and all() is called, then the 'day' value is equal to date(2026, 1, 1) and type(value) is datetime.date (not datetime.datetime).

### FR-JSON-003: The system shall persist a timezone-aware datetime.datetime value stored in a document by JSONStorage so that, after the database is reopened, the value read back is timezone-aware with the same UTC offset and equal to the original.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: CONFIRMED ("Timezone-aware datetimes keep their UTC offset; naive datetimes stay naive.")
- Links: related: Q-004
- Acceptance criteria:
  - **FR-JSON-003.AC-1**: Given a document {'when': datetime(2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))} inserted into a JSONStorage-backed database that is then closed, when the file is reopened and all() is called, then the value is equal to the original, value.utcoffset() == timedelta(hours=5, minutes=30), and value.tzinfo is not None.
  - **FR-JSON-003.AC-2**: Given a document {'when': datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)} inserted into a JSONStorage-backed database that is then closed, when the file is reopened and all() is called, then value.utcoffset() == timedelta(0) and the value is equal to the original.
  - **FR-JSON-003.AC-3**: Given one document with a naive datetime(2026, 1, 1, 12, 0) and one with the same wall time and tzinfo=timezone(timedelta(hours=-8)), both inserted and the database closed, when the file is reopened and all() is called, then the first value has tzinfo None and the second has utcoffset() == timedelta(hours=-8).

### FR-JSON-004: The system shall return a string value that merely looks like a date or datetime, stored in a document by JSONStorage, as a str with the identical text after the database is reopened.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: CONFIRMED ("Strings that merely look like dates (e.g. `"2026-01-01"`) must stay strings.")
- Links: related: Q-002
- Acceptance criteria:
  - **FR-JSON-004.AC-1**: Given a document {'a': '2026-01-01', 'b': '2026-01-01T12:00:00', 'c': '2026-01-01T12:00:00+05:30'} inserted into a JSONStorage-backed database that is then closed, when the file is reopened and all() is called, then each of 'a', 'b' and 'c' has type str and is equal to the text that was inserted.
  - **FR-JSON-004.AC-2**: Given a document containing both the string '2026-01-01' under key 's' and date(2026, 1, 1) under key 'd', inserted and the database closed, when the file is reopened and all() is called, then type of 's' is str and type of 'd' is datetime.date.

### FR-JSON-005: The system shall let an existing Query comparison between a document field and a datetime or date value match documents correctly after the database has been reopened from a JSONStorage file.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: CONFIRMED ("so that normal comparisons in queries (e.g. `Query().when < datetime(2026, 1, 1)`) work after reopening.")
- Links: CON-003, FR-JSON-001, FR-JSON-002, FR-JSON-003
- Acceptance criteria:
  - **FR-JSON-005.AC-1**: Given documents {'when': datetime(2025, 6, 1, 12, 0)} and {'when': datetime(2026, 6, 1, 12, 0)} inserted into a JSONStorage-backed database that is then closed and reopened, when db.search(Query().when < datetime(2026, 1, 1)) is called, then exactly one document is returned and its 'when' equals datetime(2025, 6, 1, 12, 0).
  - **FR-JSON-005.AC-2**: Given documents {'day': date(2025, 6, 1)} and {'day': date(2026, 6, 1)} inserted into a JSONStorage-backed database that is then closed and reopened, when db.search(Query().day >= date(2026, 1, 1)) is called, then exactly one document is returned and its 'day' equals date(2026, 6, 1).
  - **FR-JSON-005.AC-3**: Given a document {'when': datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)} persisted and the database reopened, when db.search(Query().when == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)) is called, then exactly one document is returned.

### CON-001: The implementation shall not add any new third-party dependency to the tinydb package.
- Kind: CON · Priority: MUST · Status: **READY**
- Source: CONFIRMED ("No new third-party dependencies")
- Acceptance criteria:
  - **CON-001.AC-1**: Given the project's dependency declaration (pyproject.toml) before and after the change, when the runtime dependency lists are compared, then the after-change list contains no entry that the before-change list lacks.
  - **CON-001.AC-2**: Given the changed tinydb package modules, when their import statements are collected, then every imported top-level module is either in the Python standard library or in the tinydb package itself.

### CON-002: The implementation shall leave MemoryStorage behaviour unchanged.
- Kind: CON · Priority: MUST · Status: **READY**
- Source: CONFIRMED ("`MemoryStorage` needs no change.")
- Acceptance criteria:
  - **CON-002.AC-1**: Given a TinyDB on MemoryStorage with a document {'when': datetime(2026, 1, 1)} inserted, when all() is called, then the returned document's 'when' is the identical datetime object value, equal to datetime(2026, 1, 1) (same behaviour as before the change).
  - **CON-002.AC-2**: Given the repository after the change, when git diff of the MemoryStorage class in tinydb/storages.py against the base commit is taken, then the diff for that class is empty.

### CON-003: The implementation shall add no new query operators and shall make no change to the Query class.
- Kind: CON · Priority: MUST · Status: **READY**
- Source: CONFIRMED ("No new query operators and no change to `Query`.")
- Acceptance criteria:
  - **CON-003.AC-1**: Given the repository after the change, when git diff of tinydb/queries.py against the base commit is taken, then the diff is empty.
  - **CON-003.AC-2**: Given the public attribute names of the Query class before and after the change, when dir(Query) is compared, then the two sets of names are identical.

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P3 | Must datetime and date values nested inside dicts or lists within a document also round-trip? | (a) Yes, at any nesting depth; (b) Top-level fields only (default: (a), recorded as ASM-001 (PROVISIONAL)) | none yet (candidate behaviour for nested values) |
| Q-002 | P3 | How must the on-disk representation tell a stored date or datetime from a plain string or dict, and may it be a non-plain JSON encoding? What if a user stores a dict that looks like the encoding? | (a) Format is free; collisions are documented as a limitation; (b) Collisions must round-trip as the original dict; (c) The file must stay readable by plain JSON tools without datetime-specific decoding (default: (a), recorded as ASM-002 (PROVISIONAL)) | none yet (FR-JSON-004 is READY on its stated cases) |
| Q-003 | P3 | Are other temporal types (datetime.time, datetime.timedelta) or datetime subclasses (e.g. pandas.Timestamp) in scope? | (a) Out of scope, behaviour unchanged; (b) time and timedelta also supported (default: (a), recorded as out of scope) | none yet |
| Q-004 | P3 | For aware datetimes, is preserving the UTC offset enough, or must the tzinfo class or zone name (e.g. ZoneInfo('Europe/Berlin')) be preserved? | (a) Offset only; the tzinfo may come back as datetime.timezone; (b) Preserve the zone name (default: (a), recorded as ASM-003 (PROVISIONAL), which matches the quote) | none yet |
| Q-005 | P3 | Must existing JSON files without dates, and callers who pass their own json kwargs (e.g. `default`, `cls`, `indent`) to JSONStorage, keep working exactly as before? | (a) Yes, unchanged behaviour for files and kwargs that do not involve dates; (b) No guarantee (default: (a), recorded as ASM-004 (PROVISIONAL)) | none yet |

## Terms

- TERM-001 **"Better datetime support" / "out of the box"**: Persistence round-trip of datetime/date in JSONStorage (chosen by maintainer decision 1) / New query operators or helpers for dates (excluded by maintainer decision 5) / Parsing of date-like strings (excluded by maintainer decision 3) / Support for other storages (MemoryStorage excluded by decision 4)
- TERM-002 **"same type and the same value"**: datetime == original and type is exactly datetime.datetime or datetime.date (used in the acceptance criteria) / Equal value only, with no type check (rejected: the quote says same type) / Identical tzinfo class as well (not stated; see Q-004)
- TERM-003 **"keep their UTC offset"**: utcoffset() of the value read back equals the original's, with the instant unchanged (used in the acceptance criteria) / tzinfo object identity or class preserved, e.g. ZoneInfo name (not stated; see Q-004)
- TERM-004 **"inside documents"**: Top-level fields of a document / Also values nested in dicts and lists within a document (see Q-001)
- TERM-005 **Priority words**: "must" in the maintainer's decisions maps to MUST; plain declarative statements about constraints ('No new...', 'needs no change') are mapped to MUST.

## Assumptions

- ASM-001: Datetime and date values nested in dicts and lists inside a document also round-trip (candidate: 'If nested values are in scope (Q-001), the system shall round-trip them'). (risk if wrong: Nested-value tests or behaviour would be built for a scope the maintainer did not want, or required nested support would be missed.)
- ASM-002: The on-disk encoding is a free design choice, and a user dict that mimics the encoding is a documented limitation. (risk if wrong: Data corruption on read for such dicts, or incompatibility with external JSON readers.)
- ASM-003: Preserving the UTC offset is sufficient. The tzinfo class or zone name need not be preserved. (risk if wrong: Users of ZoneInfo or DST-aware zones would lose zone semantics after reopening.)
- ASM-004: Existing database files and JSONStorage calls that do not involve dates behave exactly as before. (risk if wrong: A regression for existing users, or unneeded compatibility work.)
- ASM-005: The maintainer (iDheer) is the decision owner for this issue. (risk if wrong: Decisions in SRC-2 may not bind the scope.)

## Out of scope

- Storages other than JSONStorage; MemoryStorage is unchanged (SRC-2 decision 4)
- New query operators or any change to Query (SRC-2 decision 5)
- Parsing strings that look like dates into date objects (SRC-2 decision 3)
- New third-party dependencies (SRC-2 decision 4)
- datetime.time, datetime.timedelta and other date/time libraries (pending Q-003, default out of scope)
- Preserving timezone names or tzinfo classes beyond the UTC offset (pending Q-004)
- Date-specific convenience helpers or formatting options

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|
| FR-JSON-001.AC-1 | yes | Concrete starting state, single reopen-and-read action, and observable result (value equality, type, tzinfo None) are all specified. |
| FR-JSON-001.AC-2 | yes | Given a non-existent path and a single insert, the outcome is a precise observable: no exception is raised. |
| FR-JSON-002.AC-1 | yes | Concrete date value, round-trip via reopen, and exact type check (date, not datetime) are all observable. |
| FR-JSON-003.AC-1 | yes | Specific tzinfo offset, round-trip equality, utcoffset value and non-None tzinfo are all checkable. |
| FR-JSON-003.AC-2 | yes | UTC datetime round-trip with utcoffset()==timedelta(0) and equality is concretely assertable. |
| FR-JSON-003.AC-3 | yes | Naive and -08:00 aware values with specified tzinfo/utcoffset results after reopen are precisely checkable. |
| FR-JSON-004.AC-1 | yes | Three specific strings must come back as type str and equal to the inserted text, which is directly assertable. |
| FR-JSON-004.AC-2 | yes | A string '2026-01-01' and a date under different keys must return str and date types respectively; concrete and checkable. |
| FR-JSON-005.AC-1 | yes | Concrete datetime documents, a specific query with <, and an exact expected count and value are all defined. |
| FR-JSON-005.AC-2 | yes | Concrete date documents, a >= date query, and an exact expected single result are defined. |
| FR-JSON-005.AC-3 | yes | A timezone-aware equality query on a persisted document has a concrete expected count of exactly one. |
| CON-001.AC-1 | yes | Comparing before/after runtime dependency lists in pyproject.toml is a mechanical check with a clear pass condition. |
| CON-001.AC-2 | yes | Collecting imports from changed modules and checking against stdlib plus tinydb is mechanically verifiable, though it needs a defined list of changed modules, which the criterion supplies as 'the changed tinydb package modules'. |
| CON-002.AC-1 | yes | MemoryStorage round-trip with a naive datetime and an identity/equality check is concrete and assertable. |
| CON-002.AC-2 | yes | An empty git diff for a named class against the base commit is a mechanical check, though extracting the class's diff hunk requires tooling; still determinable. |
| CON-003.AC-1 | yes | An empty git diff of tinydb/queries.py against the base commit is a concrete mechanical check. |
| CON-003.AC-2 | yes | Comparing dir(Query) before and after is a concrete set-equality check, assuming the pre-change snapshot is captured. |

## Stage check: PASSED

