# spec.md: Add an `append` update operation for list fields in tinydb.operations

- Issue: #4 https://github.com/iDheer/tinydb/issues/4
- Verdict (A1 skill): **READY-WITH-OPEN-ITEMS**, stakeholder mode: unavailable

The issue is a precise feature request with one clear API (`append(field, value)` in `tinydb.operations`, used as `db.update(append('tags', 'urgent'), Query().id == 7)`) and one stated edge case (a missing field becomes a one-element list). It yields two READY core requirements. The repository's `tinydb/operations.py` has `delete`, `add`, `subtract`, `set`, `increment` and `decrement`. Each returns a `transform(doc)` closure that mutates the document in place, and `append` does not exist yet. Unstated edge cases are recorded as P3 questions and do not block the stated behaviour: a non-list existing field, a list passed as the value, and sharing of the value object. The stakeholder mode is `unavailable`, so the verdict is READY-WITH-OPEN-ITEMS. No P1 or P2 questions or conflicts are open. The issue text contains no embedded instructions. No tool calls were made, and there are no tool-answerable questions because the issue names no external standard or product.

## Requirements

### FR-OPS-001: The system shall provide an `append(field, value)` update operation in `tinydb.operations` that, when applied to a document that has a list in `field`, adds `value` to the end of that list.
- Kind: FR · Priority: SHOULD · Status: **READY**
- Source: STATED ("It would be nice to have this built in next to `increment`, `add`, `set` and friends in `tinydb.operations`, e.g. from tinydb.operations import append / db.update(append('tags', 'urgent'), Query().id == 7)")
- Links: ACT-1, related: Q-001, related: Q-002, related: Q-003
- Acceptance criteria:
  - **FR-OPS-001.AC-1**: Given a TinyDB database containing the document {'id': 7, 'tags': ['a']}, when `from tinydb.operations import append` is executed and then `db.update(append('tags', 'urgent'), Query().id == 7)` is called, then the import succeeds and `db.get(Query().id == 7)['tags'] == ['a', 'urgent']`.
  - **FR-OPS-001.AC-2**: Given a database containing {'id': 7, 'tags': ['a']} and {'id': 8, 'tags': ['b']}, when `db.update(append('tags', 'urgent'), Query().id == 7)` is called, then the document with id 8 still has `tags == ['b']`, i.e. only matching documents are changed.
  - **FR-OPS-001.AC-3**: Given a plain dict `doc = {'tags': ['a']}`, when `append('tags', 'urgent')(doc)` is called, then `doc == {'tags': ['a', 'urgent']}`, so the returned callable mutates the document in place like the other operations.
  - **FR-OPS-001.AC-4**: Given a database containing {'id': 7, 'tags': ['a']}, when `db.update(append('tags', 'urgent'), Query().id == 7)` is called twice, then `db.get(Query().id == 7)['tags'] == ['a', 'urgent', 'urgent']`, i.e. each call appends one element and nothing is de-duplicated.

### FR-OPS-002: The system shall, when a document matched by `append(field, value)` has no `field`, create `field` as a list containing only `value`.
- Kind: FR · Priority: MUST · Status: **READY**
- Source: STATED ("If a matching document doesn't have the field yet, it should be created as a list containing just that value.")
- Links: ACT-1, related: FR-OPS-001
- Acceptance criteria:
  - **FR-OPS-002.AC-1**: Given a database containing the document {'id': 7} with no 'tags' key, when `db.update(append('tags', 'urgent'), Query().id == 7)` is called, then `db.get(Query().id == 7)['tags'] == ['urgent']`.
  - **FR-OPS-002.AC-2**: Given a plain dict `doc = {'id': 7}`, when `append('tags', 'urgent')(doc)` is called, then `doc == {'id': 7, 'tags': ['urgent']}` and no exception is raised.
  - **FR-OPS-002.AC-3**: Given a database containing {'id': 7} and {'id': 8, 'tags': ['b']}, both matched by `Query().id.one_of([7, 8])`, when `db.update(append('tags', 'urgent'), Query().id.one_of([7, 8]))` is called, then id 7 has `tags == ['urgent']` and id 8 has `tags == ['b', 'urgent']`.

## Open questions

| Q | Priority | Question | Options / default | Blocks |
|---|---|---|---|---|
| Q-001 | P3 | What should `append` do when `field` exists but its value is not a list (e.g. a string, number, or None)? | Raise an exception, as `add`/`increment` do for incompatible types (which exception type?); Silently replace the value with a one-element list; Leave the document unchanged (default: Raise an exception and leave the document unchanged. Recorded as ASM-001 (PROVISIONAL), consistent with how the other operations fail on incompatible types.) | none yet |
| Q-002 | P3 | If `value` is itself a list, should it be added as one element or have its items added individually (see TERM-001)? | Added as one nested element (like `list.append`); Items added individually (like `list.extend`); Out of scope here; a separate `extend` operation could be requested later (default: One nested element, matching `list.append` and the name `append`. Recorded as ASM-002 (PROVISIONAL).) | none yet |
| Q-003 | P3 | Should the created list or the appended value be isolated from the object the caller passed in (copy), or may it share it? | No copy, consistent with `set`; Copy the value for each document (default: No copy, consistent with `set`. Recorded as ASM-003 (PROVISIONAL).) | none yet |
| Q-004 | P3 | Should the change also add a changelog entry and mention `append` in the usage docs? | Docstring only; Docstring plus a docs/changelog.rst entry; Docstring, changelog, and docs/usage.rst mention (default: Docstring only. The change log is left to the maintainer.) | none yet |

## Terms

- TERM-001 **appends a value**: Single element: the value is added as one element, as `list.append` does, so `append('tags', ['x','y'])` gives `[..., ['x','y']]` / Extend semantics: if the value is a list, its items are added individually / The issue's examples use only scalar (string) values, so both readings are consistent with them
- TERM-002 **list field**: A field whose stored JSON value is an array (a Python `list`) / Any mutable sequence stored under the field. JSON storage can only hold lists, so this has no practical difference for the default storage
- TERM-003 **Priority-word mapping**: 'It would be nice to have' maps to SHOULD (want / would like). The statement 'it should be created as a list' is a plain behavioural sentence and maps to MUST.

## Assumptions

- ASM-001: For a non-list existing field, `append` fails like the other operations on incompatible types and does not silently overwrite the data. Linked to Q-001. (risk if wrong: A hidden test or user expecting silent replacement or a specific exception type would fail. Impact is low because the issue does not cover this case.)
- ASM-002: A list passed as `value` is appended as a single element, as with `list.append`. Linked to Q-002. (risk if wrong: Users who expect extend semantics get nested lists.)
- ASM-003: The requester (iDheer, the issue author) is the decision owner for these questions. The maintainer decides what is merged. (risk if wrong: Defaults may be changed in review.)
- ASM-004: `append` follows the existing operation contract: a function `append(field, value)` returns a `transform(doc)` callable that mutates the document in place and returns None. This is consistent with the issue's own custom transform, with `increment`/`add`/`set`, and with how `Table.update` applies callables. (risk if wrong: Acceptance criteria that call the transform directly (FR-OPS-001.AC-3, FR-OPS-002.AC-2) would need rewriting. The db.update-based criteria still hold.)

## Out of scope

- Other list operations such as extend, remove, insert or pop (not requested).
- De-duplication of values (the issue gives no unique-add semantics).
- Nested or dotted field paths (the issue shows only top-level fields).
- Changes to Table.update, Query, storages or middlewares.
- Changing the behaviour of the existing operations (delete, add, subtract, set, increment, decrement).
- Behaviour for a non-list existing field, a list-valued argument, and copying of the value are open P3 questions (Q-001 to Q-003) and not part of the agreed core.

## Testability judge (Haiku 5.5)

| AC | Testable | Reason |
|---|---|---|
| FR-OPS-001.AC-1 | yes | Concrete starting document, one import plus one update call, and an exact stored list value ['a', 'urgent'] to assert. |
| FR-OPS-001.AC-2 | yes | Two named documents and a filtered update; the non-matching document's tags must remain exactly ['b']. |
| FR-OPS-001.AC-3 | yes | Calling the returned callable on a plain dict has a single observable result: the dict equals {'tags': ['a', 'urgent']} afterwards. |
| FR-OPS-001.AC-4 | yes | Two identical update calls with a defined expected final list ['a', 'urgent', 'urgent'] make the no-deduplication behaviour directly assertable. |
| FR-OPS-002.AC-1 | yes | A document without a 'tags' key is a concrete starting state, and the expected result ['urgent'] is an exact value. |
| FR-OPS-002.AC-2 | yes | The expected dict {'id': 7, 'tags': ['urgent']} and the absence of an exception are both checkable assertions. |
| FR-OPS-002.AC-3 | yes | Two documents, one missing 'tags' and one with ['b'], are updated by a one_of query; the exact resulting lists for ids 7 and 8 are specified. |

## Stage check: PASSED

