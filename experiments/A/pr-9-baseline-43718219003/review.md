<!-- autose -->
# Independent review: PR #9, round 1

**Verdict: ❌ REQUEST CHANGES** → route: `design`

Reviewer: claude-opus-5-5 in a separate job, contents:read token, saw only the issue, the diff and the repository at the PR head.

The PR puts the feature in the wrong place. It adds a `Table.append_to` method, but the issue asks for an `append(field, value)` operation in `tinydb.operations`, so `from tinydb.operations import append` fails with ImportError. The new method does append correctly and creates a one-element list for missing fields, and the full suite passes (229 tests). Because the requested API is missing, this goes back to design.

## Requirements from the issue (reviewer's reading)

| Requirement | Met | Evidence |
|---|---|---|
| `append` operation exists in `tinydb.operations` and works with `db.update` | no | The diff leaves tinydb/operations.py unchanged (it still only has delete/add/subtract/set/increment/decrement, lines 16-75). Probe: `from tinydb.operations import append` -> "ImportError: cannot import name 'append' from 'tinydb.operations'"; `hasattr(ops, 'append')` -> False. The PR adds a new `Table.append_to(field, value, cond)` method instead (tinydb/table.py:531-541). |
| Appends to an existing list field | partly | Only through the new `db.append_to` method. Probe: `db.append_to('tags','urgent', Query().id == 7)` -> [1], and the doc became {'id': 7, 'tags': ['a', 'urgent']}. The API the issue asked for is still missing. |
| Missing field is created as a one-element list | partly | Only through `append_to`. Probe: doc {'id': 8} became {'id': 8, 'tags': ['x']}. Each document gets its own list, not a shared one (the probe on db2 showed separate ['y'] lists). Not available via operations. |
| Tests cover the new operation | partly | tests/test_append_to.py tests `db.append_to` for the existing-list and missing-field cases. There is no test for `tinydb.operations.append` (which does not exist), and nothing was added to tests/test_operations.py. |
| Existing behaviour not broken | yes | `python -m pytest -q` -> 229 passed in 1.00s. |
| ARCHITECTURE constraints C1–C5 hold | yes | append_to delegates to self.update, which writes through _update_table (C3). It adds no imports (C4) and no dependencies (C5). Storages and queries are untouched (C1, C2). |

## Findings

| Severity | Category | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|---|
| major | approach | `tinydb/table.py:531` | The issue asks for an `append(field, value)` factory in `tinydb.operations`, next to increment/add/set, to be passed to `db.update(...)`. The PR adds a new `Table.append_to(field, value, cond)` method on the Table API instead and leaves `tinydb/operations.py` unchanged. The user's example `from tinydb.operations import append` fails with ImportError. This also goes against ARCHITECTURE.md component 6, which says update transforms live in operations.py, and it widens the Table public API without need. | Probe output: "operations.append exists: False" and "ImportError: cannot import name 'append' from 'tinydb.operations'". The diff touches only tinydb/table.py and adds tests/test_append_to.py. | Add `def append(field: str, value: Any) -> Callable[[MutableMapping], None]` to tinydb/operations.py with a transform `doc.setdefault(field, []).append(value)`. Do not add `Table.append_to` (or justify it separately). Add tests to tests/test_operations.py covering the existing-list and missing-field cases via `db.update(append(...), cond)`. |
| minor | tests | `tests/test_append_to.py:1` | The tests cover only the new Table method, not the operation the issue asked for. They also sit in a new file instead of tests/test_operations.py, where the other operations are tested. If the existing field is not a list (for example a string), the code raises AttributeError, and no test covers or documents that. | tests/test_append_to.py calls only `db.append_to`. | Move the tests into tests/test_operations.py and target `operations.append`. You could also add a test that pins down the behaviour when the field is not a list. |

## Commands the reviewer actually ran

- `python -m pytest -q`
- `python /home/runner/work/_temp/autose/review-scratch/probe_append.py`

## Risks considered

- API mismatch: the requested `tinydb.operations.append` does not exist
- A mutable default list shared between documents (not the case: setdefault creates a new list per call)
- Writes bypassing _update_table / cache invalidation (C3): not the case, because it delegates to update()
- Import layering and stdlib-only constraints (C4/C5): unaffected
- Non-list existing field: raises AttributeError, untested
- TinyDB attribute forwarding exposing the new Table method on the db object, which grows the public API surface

<sub>cost $0.123, 8 turns</sub>
