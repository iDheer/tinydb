# spec.md: Better datetime support in TinyDB (issue #5)

- Issue: #5 https://github.com/iDheer/tinydb/issues/5
- Verdict (A1 skill): **DRAFT**, stakeholder mode: unavailable

The issue is a vague wish with no concrete behaviour, so the verdict is DRAFT. It names three pain points: converting dates to strings and back, hacky date comparison in queries, and wanting this "out of the box". It does not say which date types, whether the change is automatic or opt-in, what on-disk format to use, or how existing data and timezones are handled. The repo shows the current behaviour: `tinydb/storages.py:147` has `JSONStorage.write` call `json.dumps(data, **self.kwargs)` with no date handling, so inserting a `datetime` with the default storage should fail with a `TypeError`. Dates must therefore be hand-converted to strings, and queries can only compare them as strings. I did not run this. I wrote 3 stated functional requirements and 1 constraint, all NEEDS-CLARIFICATION, plus 2 candidate requirements. Three P1 questions should go to the maintainer first: type scope, where the feature lives, and how values are read back. Stakeholder mode is `unavailable` and no maintainer comments were supplied, so nothing is CONFIRMED. No tool-answerable questions exist (nothing public is named), so no tool calls were made. The issue contains no embedded instructions.

## Requirements

### FR-DATE-001: The system shall accept a Python date/time value inside a document on insert without the caller first converting it to a string.
- Kind: FR · Priority: SHOULD · Status: **NEEDS-CLARIFICATION**
- Source: STATED ("I always end up converting things to strings and back myself")
- Links: blocked by: Q-001, Q-002, related: Q-005, Q-008, TERM-001, TERM-003, GOAL-001
- Acceptance criteria:
  - **FR-DATE-001.AC-1**: Given a TinyDB instance on a new temporary JSON file using the default storage, when db.insert({'when': datetime(2024, 1, 2, 3, 4, 5)}) is called, then no exception is raised and the file on disk contains valid JSON. Baseline today: json.dumps raises TypeError..
  - **FR-DATE-001.AC-2**: Given a TinyDB instance on a new temporary JSON file using the default storage, when db.insert({'day': date(2024, 1, 2)}) is called, then <TBD: Q-001> (whether plain dates, times and timedeltas are in scope).

### FR-DATE-002: The system shall return a stored date/time value as a Python date/time object when the document is read back, without the caller converting it from a string.
- Kind: FR · Priority: SHOULD · Status: **NEEDS-CLARIFICATION**
- Source: STATED ("I always end up converting things to strings and back myself")
- Links: blocked by: Q-001, Q-002, Q-003, related: Q-005, Q-006, TERM-001, TERM-003
- Acceptance criteria:
  - **FR-DATE-002.AC-1**: Given a JSON file written by one TinyDB instance after insert({'when': datetime(2024, 1, 2, 3, 4, 5)}), when a new TinyDB instance opens the same file and db.all() is called, then db.all()[0]['when'] == datetime(2024, 1, 2, 3, 4, 5) and isinstance(..., datetime) is True.
  - **FR-DATE-002.AC-2**: Given a document inserted with {'note': '2024-01-02T03:04:05'} (an ordinary string), when the document is read back via db.all(), then <TBD: Q-003> (whether date-like strings stay strings or become datetime).

### FR-DATE-003: The system shall let a query compare a stored date/time field against a Python date/time value directly, without the caller converting either side to a string.
- Kind: FR · Priority: SHOULD · Status: **NEEDS-CLARIFICATION**
- Source: STATED ("comparing dates in queries feels hacky")
- Links: blocked by: Q-001, Q-002, Q-003, Q-004, related: Q-006, TERM-004
- Acceptance criteria:
  - **FR-DATE-003.AC-1**: Given a table holding three documents with 'when' set to datetime(2024, 1, 1), datetime(2024, 6, 1) and datetime(2024, 12, 1), when db.search(Query().when > datetime(2024, 3, 1)) is called, then exactly the documents with datetime(2024, 6, 1) and datetime(2024, 12, 1) are returned.
  - **FR-DATE-003.AC-2**: Given the same three documents, when db.search(Query().when == datetime(2024, 6, 1)) is called, then exactly the document with datetime(2024, 6, 1) is returned.
  - **FR-DATE-003.AC-3**: Given the same three documents, when a range, date-only, or string-argument comparison is used, then <TBD: Q-004> (which comparison forms are required).

### CON-DATE-001: Date/time handling shall work 'out of the box' (the exact reading is open: automatic with the default storage, or opt-in via a bundled helper).
- Kind: CON · Priority: SHOULD · Status: **NEEDS-CLARIFICATION**
- Source: STATED ("Would be great if TinyDB handled dates better out of the box.")
- Links: blocked by: Q-002, TERM-003, GOAL-001
- Acceptance criteria:
  - **CON-DATE-001.AC-1**: Given a TinyDB instance created with the setup that Q-002 defines as 'out of the box', when a datetime is inserted and read back, then <TBD: Q-002> (required configuration, e.g. none versus one explicit argument).

### FR-DATE-004: CANDIDATE (not agreed): The system shall keep reading existing database files that contain date strings written by earlier versions without raising an error.
- Kind: FR · Priority: UNSET · Status: **ASSUMPTION-ONLY**
- Source: ASSUMED ("")
- Links: ASM-003, Q-005
- Acceptance criteria:
  - **FR-DATE-004.AC-1**: Given a JSON file containing {"_default": {"1": {"when": "2024-01-02T03:04:05"}}}, when TinyDB(path).all() is called, then one document with doc_id 1 is returned and no exception is raised.

### FR-DATE-005: CANDIDATE (not agreed): The system shall preserve the UTC offset of a timezone-aware datetime across a store and read-back round trip.
- Kind: FR · Priority: UNSET · Status: **NEEDS-CLARIFICATION**
- Source: ASSUMED ("")
- Links: blocked by: Q-006, ASM-004
- Acceptance criteria:
  - **FR-DATE-005.AC-1**: Given a stored document with 'when' = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc), when the document is read back from a re-opened database file, then the value equals the original and its utcoffset() == timedelta(0).

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P1 | Which date/time types must be supported: datetime only, date and datetime, or also time and timedelta? Are timezone-aware values in scope? | (a) datetime only; (b) date and datetime; (c) date, time, datetime, timedelta; (d) any of the above, naive and timezone-aware (default: (b), recorded as ASM-002 (PROVISIONAL); it narrows 'dates' only if the maintainer wants times or timedeltas.) | FR-DATE-001, FR-DATE-002, FR-DATE-003 |
| Q-002 | P1 | What does 'out of the box' mean, and where should the feature live: automatic in the default JSONStorage, an opt-in option or middleware shipped in TinyDB, or only a documented recipe or extension? Does it apply to other storages (MemoryStorage, custom ones)? | (a) automatic in default JSONStorage; (b) opt-in bundled middleware or storage argument; (c) separate extension or documentation only; (d) works with any storage (default: No default: maintainer decision required (design-level scope choice).) | CON-DATE-001, FR-DATE-001, FR-DATE-002, FR-DATE-003 |
| Q-003 | P1 | When reading, should stored date values be returned as Python date/time objects, and how should a string the user inserted that merely looks like a date be treated (left as string, or converted)? | (a) only values that were inserted as date objects come back as date objects (a type marker is stored); (b) any ISO-8601-looking string is converted on read; (c) values come back as strings and only queries understand dates (default: (a), recorded as ASM-005 (PROVISIONAL). It narrows 'converting back' to type-tagged values.) | FR-DATE-002, FR-DATE-003, FR-DATE-004 |
| Q-004 | P2 | Which query comparisons are required: <, <=, >, >=, == against date/time objects; ranges; same-day matching on a datetime; comparison against strings; or dedicated helper methods? | (a) the standard comparison operators only; (b) operators plus a between/range helper; (c) also same-day or date-part matching; (d) also accept ISO strings as arguments (default: (a), recorded as ASM-006 (PROVISIONAL).) | FR-DATE-003 |
| Q-005 | P2 | What on-disk representation is required, and must existing database files that contain date strings stay readable and unchanged? | (a) ISO 8601 strings with a type marker; (b) plain ISO 8601 strings, no marker; (c) epoch numbers; (d) no constraint (default: No default: maintainer value needed. Existing files remaining readable is provisionally ASM-003.) | FR-DATE-004 |
| Q-006 | P2 | How should timezones be handled: preserved on round trip, normalised to UTC, or left naive? What should happen when a query compares a naive value with an aware one (Python raises TypeError)? | (a) preserve tzinfo and offset; (b) normalise to UTC; (c) naive only; (d) raise a clear error on mixing (default: (a), recorded as ASM-004 (PROVISIONAL).) | FR-DATE-005, FR-DATE-003 |
| Q-007 | P2 | Who has decision authority over scope: the maintainer, as the issue author? Is the issue author a maintainer? | (a) the repository maintainer decides; (b) another named person decides (default: (a), recorded as ASM-001 (PROVISIONAL).) | none yet |
| Q-008 | P3 | What should happen on a value that cannot be handled, and should the user documentation get examples? | (a) raise a TypeError as today; (b) a clearer error message; (c) docs update required, or not (default: (a) plus a docs example, recorded as ASSUMED with no requirement.) | none yet |

## Terms

- TERM-001 **dates**: datetime.datetime only / datetime.date and datetime.datetime / date, time, datetime and timedelta / also timezone-aware values / also epoch numbers or ISO strings supplied by the caller
- TERM-002 **better**: no manual conversion needed for storage and retrieval / more convenient query syntax / all of these, plus timezone correctness and documentation
- TERM-003 **out of the box**: automatic in the default JSONStorage with no configuration / opt-in through a bundled middleware or storage option / a separate extension package / TinyDB core vs. a documented recipe only
- TERM-004 **comparing dates in queries**: <, <=, >, >=, == against datetime objects / range or between queries / date-only comparison on stored datetimes (same day) / comparison against ISO strings supplied by the caller / query helpers such as Query().field.after(...)
- TERM-005 **hacky**: requires manual string conversion on both sides / relies on ISO strings sorting lexicographically / requires a custom test() lambda

## Assumptions

- ASM-001: The issue author or repository maintainer is the decision owner and the only requester. (risk if wrong: Answers to questions may come from the wrong person and have to be redone.)
- ASM-002: 'dates' includes at least datetime.datetime and datetime.date (provisional default for Q-001). (risk if wrong: Wrong type scope leads to missing or excess behaviour for date, time and timedelta.)
- ASM-003: Existing database files with date strings must continue to load unchanged. (risk if wrong: Either a breaking change goes unnoticed, or needless compatibility work is done.)
- ASM-004: Timezone-aware datetimes keep their UTC offset across a round trip. (risk if wrong: Timezone data may be lost or normalised unexpectedly.)
- ASM-005: Only values inserted as date objects come back as date objects; ordinary strings are never converted. (risk if wrong: User strings may be silently converted, or date round trip may not work.)
- ASM-006: Query support means the standard comparison operators against date/time objects. (risk if wrong: Range or same-day queries expected by the author would be missing.)

## Out of scope

- Choosing a design or implementation (middleware vs. storage subclass vs. query helpers, serialisation format)
- Third-party extensions or other storage back-ends, unless Q-002 brings them into scope
- Time-series or calendar features such as recurrence, durations arithmetic, indexing or sorting by date
- Natural-language date parsing
- Locale-specific date formatting
- Migration tooling for existing database files (undetermined; see Q-005)

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|

## Stage check: FAILED

- spec verdict is DRAFT (the issue does not yet define what to build)
- open P1 questions: Q-001, Q-002, Q-003
- no READY MUST/SHOULD requirement
- FR-DATE-001 is NEEDS-CLARIFICATION (core requirements must be READY)
- FR-DATE-001.AC-2: contains a <TBD> placeholder
- FR-DATE-002 is NEEDS-CLARIFICATION (core requirements must be READY)
- FR-DATE-002.AC-2: contains a <TBD> placeholder
- FR-DATE-003 is NEEDS-CLARIFICATION (core requirements must be READY)
- FR-DATE-003.AC-3: contains a <TBD> placeholder
- CON-DATE-001 is NEEDS-CLARIFICATION (core requirements must be READY)
- CON-DATE-001.AC-1: contains a <TBD> placeholder
