# spec.md: Add an `append` update operation to tinydb.operations

- Issue: #4 https://github.com/iDheer/tinydb/issues/4
- Verdict (A1 skill): **READY-WITH-OPEN-ITEMS**, stakeholder mode: unavailable

Precise feature request: a new `append(field, value)` operation in `tinydb.operations` that adds a value to a list field of the documents matched by `db.update`, and creates the field as a one-element list when it is missing. Current `tinydb/operations.py` has delete, add, subtract, set, increment and decrement. Each returns a `transform(doc)` closure that mutates the document, and none of them creates a missing field (`add` and `increment` raise KeyError). The core behaviour is testable now. The unstated edge cases (field exists but is not a list, a list passed as the value, docs) are P2/P3 questions and do not block it. The stakeholder is `unavailable` (no maintainer comments), so the verdict cannot be READY. The issue contains no embedded instructions aimed at the workflow.

## Requirements

### FR-OPS-001: The system shall provide an `append(field, value)` operation in `tinydb.operations` which, when passed to `db.update`, appends `value` to the end of the list stored in `field` of each matching document.
- Kind: FR · Priority: COULD · Status: **READY**
- Source: STATED ("It would be nice to have this built in next to `increment`, `add`, `set` and friends in `tinydb.operations`, e.g.")
- Links: related: Q-002, related: Q-003, related: TERM-001
- Acceptance criteria:
  - **FR-OPS-001.AC-1**: Given a TinyDB on MemoryStorage containing {'id': 7, 'tags': ['a']} and {'id': 8, 'tags': ['b']}, when db.update(append('tags', 'urgent'), Query().id == 7) is called, then the document with id 7 has tags == ['a', 'urgent'] and the document with id 8 still has tags == ['b'].
  - **FR-OPS-001.AC-2**: Given the installed tinydb package, when `from tinydb.operations import append` is executed, then the import succeeds and `append` is callable.
  - **FR-OPS-001.AC-3**: Given a TinyDB containing {'id': 7, 'tags': []}, when db.update(append('tags', 'urgent'), Query().id == 7) is called, then the document with id 7 has tags == ['urgent'].
  - **FR-OPS-001.AC-4**: Given a TinyDB containing {'id': 1, 'tags': ['a']} and {'id': 2, 'tags': ['b']}, when db.update(append('tags', 'x'), Query().id.exists()) is called, then both documents are updated: tags == ['a', 'x'] and tags == ['b', 'x'] respectively.

### FR-OPS-002: The system shall, when a matching document does not have the field passed to `append`, create that field as a list containing only the appended value.
- Kind: FR · Priority: SHOULD · Status: **READY**
- Source: STATED ("If a matching document doesn't have the field yet, it should be created as a list containing just that value.")
- Links: related: Q-002
- Acceptance criteria:
  - **FR-OPS-002.AC-1**: Given a TinyDB containing {'id': 7} with no 'tags' key, when db.update(append('tags', 'urgent'), Query().id == 7) is called, then the document with id 7 has tags == ['urgent'] and no exception is raised.
  - **FR-OPS-002.AC-2**: Given a TinyDB containing {'id': 7} and {'id': 8}, neither with a 'tags' key, when db.update(append('tags', 'urgent'), Query().id == 7) is called, then document 7 has tags == ['urgent'] and document 8 still has no 'tags' key.
  - **FR-OPS-002.AC-3**: Given a TinyDB containing {'id': 7} and {'id': 8, 'tags': ['a']}, when db.update(append('tags', 'urgent'), Query().id.exists()) is called, then document 7 has tags == ['urgent'] and document 8 has tags == ['a', 'urgent'].

### FR-OPS-003: If Q-002 is answered 'single element', the system shall append `value` as one element even when `value` is itself a list (the list is not flattened).
- Kind: FR · Priority: UNSET · Status: **ASSUMPTION-ONLY**
- Source: ASSUMED ("Candidate, not agreed. Basis: the operation name `append` in `append('tags', 'urgent')` (SRC-1). No source states how a list-valued argument is treated.")
- Links: ASM-001, Q-002
- Acceptance criteria:
  - **FR-OPS-003.AC-1**: Given a TinyDB containing {'id': 7, 'tags': ['a']}, when db.update(append('tags', ['x', 'y']), Query().id == 7) is called, then the document with id 7 has tags == ['a', ['x', 'y']].

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P2 | What should `append` do when the field exists but its value is not a list (e.g. a string, a number, or None)? | (a) let the natural Python error propagate (AttributeError, as the issue's own transform would do); (b) raise an explicit TypeError; (c) replace the value with a new list containing the value; (d) treat None as missing (default: (a), recorded as ASM-002 (PROVISIONAL), consistent with the other operations and with the issue's own `doc['tags'].append(tag)` snippet. No acceptance criterion depends on it until it is answered.) | none yet (dimension 3: exceptions) |
| Q-002 | P3 | If the appended value is itself a list or tuple, should it be added as one element or have its items added individually? | (a) one element (list.append semantics); (b) extend with its items (default: (a), recorded as ASM-001 (PROVISIONAL).) | FR-OPS-003 |
| Q-003 | P3 | Should the change also include documentation (docs/usage.rst, docs/api.rst) and a changelog entry in docs/changelog.rst, or only the code and tests? | (a) code and tests only; (b) also update the usage docs and the changelog (default: no default: maintainer decision (owner: repository maintainer). Not a requirement until answered.) | none yet (dimension 12: operations) |

## Terms

- TERM-001 **append (and 'list field')**: add one element at the end, like list.append, so a list argument becomes a nested element (the issue's own example transform uses doc['tags'].append(tag)) / extend the list with the items of an iterable argument / add only if the value is not already present (set-like)
- TERM-002 **friends (as in 'increment, add, set and friends')**: the existing operations in tinydb/operations.py (delete, add, subtract, set, increment, decrement), which is the reading used here / other, not yet existing operations (e.g. extend, remove) that are also requested
- TERM-003 **Priority-word mapping**: 'would be nice to have' / 'nice to have' → COULD / 'should' → SHOULD / The issue's wording 'It would be nice to have' makes FR-OPS-001 COULD. Priority is informative only and does not affect the verdict (§8.3).

## Assumptions

- ASM-001: A list-valued argument to `append` is added as a single element (list.append semantics), not flattened. (risk if wrong: If the maintainer wants extend semantics, the FR-OPS-003 acceptance criterion would assert the wrong result. This is a low risk because the stated examples use scalar values.)
- ASM-002: When the field exists but is not a list, the natural Python error propagates and no special handling is added. (risk if wrong: If a defined error or a replacement is expected, a hidden test for that case would fail. Not tested by the current acceptance criteria.)
- ASM-003: The requester (the repository owner iDheer, the issue author) is the decision owner. There is a single requester and no maintainer comment answers any question. (risk if wrong: Another maintainer may hold different views on naming or semantics. Low impact for this small feature.)
- ASM-004: `append` follows the existing calling convention of tinydb.operations: it returns a `transform(doc)` callable that mutates the document in place and returns None, usable as the first argument of `db.update`. (risk if wrong: This is implied by the issue's request to place it next to increment, add and set, and by its `db.update(append(...), ...)` usage. If it were wrong, the usage example in the issue would not work.)

## Out of scope

- Other list operations (extend, remove, insert, pop, prepend, add-if-absent).
- Appending into nested or dotted field paths (e.g. 'a.b.tags').
- Changes to Table.update, Query or storage behaviour.
- Changing the behaviour of the existing operations (delete, add, subtract, set, increment, decrement), including their handling of missing fields.
- Documentation and changelog changes, unless Q-003 is answered 'yes'.
- Design of the implementation.

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|
| FR-OPS-002.AC-1 | yes | Concrete start state ({'id': 7} without 'tags'), a single update call, and observable results (tags == ['urgent'], no exception) that a pytest test can assert directly. |
| FR-OPS-002.AC-2 | yes | Concrete two-document start state, a single targeted update, and specific observable outcomes for both document 7 (tags == ['urgent']) and document 8 (no 'tags' key) that can be asserted. |
| FR-OPS-002.AC-3 | yes | Concrete start state with one document lacking 'tags' and one holding ['a'], a single update matching both via exists(), and exact expected lists ['urgent'] and ['a', 'urgent'] that are unambiguous to assert. |

## Stage check: PASSED

