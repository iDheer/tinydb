# design.md

Add a single `append(field, value)` factory to tinydb/operations.py that returns a `transform(doc)` closure which appends to the list in `field` and creates `[value]` when the field is missing.

## Approach

Follow the existing operations convention (factory returning a `transform(doc)` closure that mutates the doc in place and returns None). Implement as `doc.setdefault(field, []).append(value)`. A missing field becomes `[value]` (FR-OPS-002), an existing list gets the value added at the end (FR-OPS-001), and a list-valued `value` is added as one element (ASM-001 / FR-OPS-003). A non-list existing value raises the natural AttributeError (ASM-002 / Q-001 default (a)). Do not call the module's `set` or any builtin shadowed by it. Update the module docstring only if desired; no docs/changelog changes, since Q-003 is unanswered and docs are out of scope. Table.update already runs the transform on each matching document and persists through `_update_table`, so no changes to table.py are needed.

## Files and symbols to change

| File | Change | Symbol | Kind | Symbol change | What |
|---|---|---|---|---|---|
| `tinydb/operations.py` | modify | `append` | function | create | `append(field: str, value: Any) -> Callable[[MutableMapping], None]`. Returns an inner `transform(doc)` that does `doc.setdefault(field, []).append(value)`. It creates the field as `[value]` when missing, appends to the end of an existing list, and does not flatten list values. It has a docstring in the style of the other operations. |

## Acceptance criteria → code → test

| AC | Symbols | Test idea |
|---|---|---|
| FR-OPS-001.AC-1 | append | TinyDB(storage=MemoryStorage) with ids 7 and 8; update(append('tags','urgent'), Query().id == 7); assert doc 7 tags == ['a','urgent'] and doc 8 tags == ['b']. |
| FR-OPS-001.AC-2 | append | `from tinydb.operations import append` succeeds and `callable(append)` is True. |
| FR-OPS-001.AC-3 | append | Doc {'id':7,'tags':[]}; update with append('tags','urgent'); assert tags == ['urgent']. |
| FR-OPS-001.AC-4 | append | Two docs with tags ['a'] and ['b']; update(append('tags','x'), Query().id.exists()); assert tags == ['a','x'] and ['b','x']. |
| FR-OPS-002.AC-1 | append | Doc {'id':7} with no tags; update with append; assert tags == ['urgent'] and no exception. |
| FR-OPS-002.AC-2 | append | Docs {'id':7} and {'id':8}; update only id 7; assert doc 7 tags == ['urgent'] and 'tags' not in doc 8. |
| FR-OPS-002.AC-3 | append | Docs {'id':7} and {'id':8,'tags':['a']}; update with Query().id.exists(); assert ['urgent'] and ['a','urgent']. |
| FR-OPS-003.AC-1 | append | Doc tags ['a']; append('tags', ['x','y']); assert tags == ['a', ['x','y']] (assumption-only AC, list.append semantics). |

## Architecture constraints (ARCHITECTURE.md)

- C1: No storage changes; the operation is storage-agnostic.
- C2: Not a query operation, so no query hash is needed. Queries are untouched.
- C3: The operation only mutates the document passed in by Table.update; persistence and cache invalidation still happen in `Table._update_table`. Nothing writes to storage directly.
- C4: operations.py gains no new imports (Any and MutableMapping are already imported) and nothing imports table/database.
- C5: Standard library only; no new dependencies.

## Alternatives considered

- Explicit `if field not in doc: doc[field] = [value] else: doc[field].append(value)`: More lines for the same behaviour; setdefault is shorter and equally clear.
- Raise TypeError when the existing value is not a list, or replace it, or treat None as missing (Q-001 b/c/d): Not requested; spec default is (a), natural Python error, consistent with the other operations. Adds behaviour that has no acceptance criterion.
- Extend semantics for list/tuple values (Q-002 b): Spec default and FR-OPS-003 use list.append semantics; the name `append` implies it.
- Build a new list (`doc[field] = doc.get(field, []) + [value]`): Fails with non-list types differently and needlessly copies the list; in-place append matches the issue's own snippet.
- Also update docs/usage.rst, docs/api.rst and docs/changelog.rst: Q-003 is unanswered (maintainer decision) and the spec lists docs as out of scope.

## Risks

- Non-list existing values (string, number, None) raise AttributeError (Q-001, default (a)); a maintainer may later want TypeError or replacement.
- A list/tuple argument is appended as a single nested element (ASM-001); the maintainer might prefer extend semantics.
- Module-level `set` in operations.py shadows the builtin, so the implementation must not use `set()` and should use setdefault, as designed.
- The append mutates the list object in place. With MemoryStorage, if a user inserted a list they still hold a reference to, that list may be mutated, because MemoryStorage does not copy. This is the same aliasing as the existing operations and is acceptable.
- Docs and changelog are not updated (Q-003 unanswered), so the new operation is undocumented until a maintainer decides.

## Stage check: PASSED

