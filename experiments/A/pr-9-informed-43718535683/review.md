<!-- autose -->
# Independent review: PR #9, round 1

**Verdict: ❌ REQUEST CHANGES** → route: `implement`

Reviewer: claude-opus-5-5 in a separate job, contents:read token, saw only the issue, the diff and the repository at the PR head.

I'm requesting changes. The issue asks for `from tinydb.operations import append` to use with `db.update`, but `tinydb.operations` still has no `append` (my probe gets an ImportError). The PR instead adds a new, unrequested public method `Table.append_to`. That goes against both the spec and the design, which say to add an `append` factory in operations.py and leave table.py alone. The method itself works: it creates a missing field as a one-element list, updates only matching documents, and goes through `_update_table`, so the query cache is cleared (C3). The full suite passes (229 tests). The tests only cover `append_to`, not the requested operation. The design is sound and the code didn't follow it, so I'm routing this back to implement: add `append` to operations.py, remove `Table.append_to`, and test the spec's acceptance criteria with `db.update(append(...), cond)`.

## Requirements from the issue (reviewer's reading)

| Requirement | Met | Evidence |
|---|---|---|
| R1: `from tinydb.operations import append` exists and works with db.update | no | Probe output: `operations.append import: FAIL cannot import name 'append' from 'tinydb.operations'`. tinydb/operations.py only defines delete, add, subtract, set, increment and decrement (lines 16-68). The diff only touches tinydb/table.py and adds a test. |
| R2: Appends to existing list of matching docs only | partly | Only through the unrequested Table.append_to (tinydb/table.py:531-541). Probe: append_to('tags','urgent', Query().id == 7) changed only doc 7; doc 9 kept ['a']. The requested db.update(append(...)) form is not available. |
| R3: Missing field created as one-element list | partly | Probe: doc {'id': 7} became {'id': 7, 'tags': ['urgent']} via append_to, and tests/test_append_to.py covers this, but not through the requested operations API. |
| R4: No regressions | yes | `python -m pytest -q`: 229 passed in 1.17s. |
| R5: C1-C5 hold | yes | append_to calls self.update, which goes through _update_table (C3). Probe: a cached Query().tags.exists() search went from 2 to 3 results after append_to, so the cache was invalidated. No new imports or dependencies (C4/C5), and storages and queries are untouched (C1/C2). |
| R6: Tests for the requested API | no | tests/test_append_to.py tests only db.append_to. There is no test for tinydb.operations.append, and none for the spec ACs FR-OPS-001.AC-1..4 or FR-OPS-002.AC-1..3 in the requested form. |

## Findings

| Severity | Category | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|---|
| major | code | `tinydb/table.py:531` | The PR does not implement what the issue, spec and design ask for. The issue explicitly wants `from tinydb.operations import append` used as `db.update(append('tags', 'urgent'), cond)`. The PR instead adds a new public method `Table.append_to(field, value, cond)` and leaves tinydb/operations.py unchanged. The design.md plan, which is sound, specifies an `append` factory in operations.py and says no table.py change is needed. The implementation ignored that plan, and the PR description rationalises the deviation. | Probe: `cannot import name 'append' from 'tinydb.operations'`. `git diff 7c7d3a2 --stat` shows only tests/test_append_to.py and tinydb/table.py changed. | Add `def append(field: str, value: Any) -> Callable[[MutableMapping], None]` to tinydb/operations.py. It should return a `transform(doc)` that runs `doc.setdefault(field, []).append(value)` and have a docstring in the style of the other operations. Remove Table.append_to. |
| minor | scope | `tinydb/table.py:531` | This adds an unrequested public API, Table.append_to (also exposed on TinyDB through forwarding). It widens the public surface with an inconsistent pattern: no other operation has a dedicated Table method. | Diff hunk @@ -528,6 +528,18 @@ in tinydb/table.py. Spec 'Out of scope' says: 'Changes to Table.update, Query or storage behaviour'. Design: 'no changes to table.py are needed'. | Drop Table.append_to and keep the change in tinydb/operations.py. |
| major | tests | `tests/test_append_to.py:1` | The tests cover only the unrequested append_to method. Nothing tests the requested operations.append, and the spec ACs (non-matching docs untouched, empty-list field, targeted update leaves other docs without the key, import succeeds) are not exercised. | tests/test_append_to.py has a single test that calls db.append_to with Query().id.exists(). | Add tests to tests/test_operations.py for `append` that cover FR-OPS-001.AC-1..4 and FR-OPS-002.AC-1..3 (plus FR-OPS-003.AC-1 for a list-valued argument), using db.update(append(...), cond). |

## Commands the reviewer actually ran

- `python -m pytest -q`
- `git diff 7c7d3a2 --stat`
- `python /home/runner/work/_temp/autose/review-scratch/probe_append.py`

## Risks considered

- The requested public API (tinydb.operations.append) is missing, so users following the issue's example get ImportError.
- Unrequested public API growth (Table.append_to / TinyDB.append_to) would be hard to remove once released.
- C3 cache invalidation: verified that it holds, because append_to delegates to update/_update_table.
- Non-list existing field values (str/None/int) raise AttributeError; acceptable per spec ASM-002 but untested.
- A list-valued argument is appended as a nested element (list.append semantics), consistent with ASM-001.
- In-place mutation aliasing with MemoryStorage: same as the existing operations.
- operations.py shadows the builtin `set`; a future implementation must not call set() there.
- The issue text contains no embedded instructions aimed at the workflow.

<sub>cost $0.156, 9 turns</sub>
