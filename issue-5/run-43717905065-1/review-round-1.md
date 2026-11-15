<!-- autose -->
# Independent review: PR #17, round 1

**Verdict: ❌ REQUEST CHANGES** → route: `implement`

Reviewer: claude-opus-5-5 in a separate job, contents:read token, saw only the issue, the diff and the repository at the PR head.

The tagged-dict encoding in JSONStorage does what the maintainer asked. Datetimes and dates round-trip with the right type, value and offset (naive stays naive), date-like strings stay strings, queries work after reopening, and MemoryStorage, Query and the dependencies are untouched. The full suite passes (245). The PR does introduce a regression: write() now always sets json.dumps' `default=`, which overrides the `default()` method of a user-supplied `cls=` encoder. `TinyDB(path, cls=MyEncoder)` setups that handled Decimal or other types now raise TypeError on insert; my probe confirmed this. Minor issues: user dicts shaped like the reserved tag are silently decoded into dates, and the tests depend on git history. The design is fine and the fix is local to the code, so I'm routing this to implement.

## Requirements from the issue (reviewer's reading)

| Requirement | Met | Evidence |
|---|---|---|
| datetime/date persist through JSONStorage and come back with the same type and value | yes | Probe: nested datetime/date values inside lists and dicts, date(1,1,1), date(999,12,31) and datetime.max all round-trip with the right types ('nested ok True'). Tests test_fr_json_001/002 pass. |
| Query comparisons work after reopen | yes | Probe 'query < 1'. Tests test_fr_json_005_ac_1..3 pass. |
| Aware datetimes keep their offset and naive ones stay naive | yes | Probe: an offset of -03:15:07.000005 is preserved ('odd_tz offset True'). Tests test_fr_json_003_* pass. |
| Date-like strings stay strings | yes | Probe: 's' stays str, and a legacy file with "2026-01-01" loads as str ('legacy'). Test test_fr_json_004_* passes. |
| No new dependencies, MemoryStorage unchanged | yes | storages.py adds only `import datetime` (stdlib). The diff does not touch MemoryStorage or pyproject.toml (git diff --stat: only storages.py and the new test file). |
| No change to Query | yes | git diff --stat shows queries.py is unchanged. |
| Existing behaviour not broken (user json.dumps kwargs, CachingMiddleware, existing files) | partly | CachingMiddleware works, legacy files load and user `default=str` still works (probe). But a user `cls=` encoder is now broken: probe prints 'base json with cls: {"x": "1.5"}' and then 'cls encoder FAIL TypeError Object of type Decimal is not JSON serializable'. |
| C1-C5 hold | yes | storages.py imports only stdlib (test_con_001_ac_2 passes). Serialisation stays in storages.py. Table, queries and the middlewares are untouched. |

## Findings

| Severity | Category | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|---|
| major | code | `tinydb/storages.py:189` | Regression: JSONStorage.write now always passes `default=` to json.dumps. When a user configured the storage with a custom encoder class (`TinyDB(path, cls=MyEncoder)`, which is forwarded to json.dumps through **kwargs and worked before), json.dumps passes our `default` to the encoder constructor. That sets `self.default` on the instance and shadows the class's `default()` method, so the user's encoder is never consulted. Any insert of a type the user's encoder handled (Decimal, UUID, set, ...) now raises TypeError. | Probe 5: `json.dumps({'x': Decimal('1.5')}, cls=DecEnc)` gives '{"x": "1.5"}' (this is the pre-PR code path, json.dumps(data, **kwargs)). `TinyDB(p, cls=DecEnc).insert({'x': Decimal('1.5')})` gives 'cls encoder FAIL TypeError Object of type Decimal is not JSON serializable'. | When neither `default` nor a custom `cls` is given, keep the current behaviour. When `cls` is given, fall back to the encoder's own `default`. One way: when `cls` is present and `default` is not, subclass it dynamically (`class _Enc(user_cls): def default(self, o): return _encode_temporal(o) if isinstance(o, datetime.date) else super().default(o)`), pass `cls=_Enc`, and do not set `default`. Add a regression test with a custom cls encoder and a datetime in the same document, and one with a user `default=`. |
| minor | code | `tinydb/storages.py:41` | Tag collision: a user document that legitimately contains a dict with exactly the keys '__tinydb_type__' and '__tinydb_value__' (for example, data copied from another TinyDB file's raw JSON) is silently turned into a date/datetime on read. This is an unlikely edge case and an accepted trade-off of tagged encoding, but it is neither documented nor tested. | Probe 6: inserting {'meta': {'__tinydb_type__': 'date', '__tinydb_value__': '2026-01-01'}} reads back as {'meta': datetime.date(2026, 1, 1)}. | Document the reserved keys in the JSONStorage docstring, or escape user dicts that use the reserved key on write. |
| nit | tests | `tests/test_autose_issue_5.py:43` | Several tests depend on git history (merge-base with main, `git show`). They skip or fail outside a git checkout (sdist, shallow CI clone), and they assert process properties (queries.py byte-identical to base) rather than behaviour. | _base() calls `git merge-base HEAD main`, and _base_file asserts the git return code is 0. | Drop the git-diff based tests or mark them as meta-checks. Keep the behavioural tests, and add tests for the cls/default kwargs. |

## Commands the reviewer actually ran

- `python -m pytest -q`
- `git diff 13eca00 --stat`
- `python /home/runner/work/_temp/autose/review-scratch/probe.py`

## Risks considered

- datetime checked before date (subclass ordering): correct
- Nested datetimes in lists and dicts: handled by the json default hook recursion
- Timezone offsets with seconds and microseconds, and fromisoformat compatibility on Python 3.12: OK
- Year < 1000 and datetime.max/date.min: OK
- Date-like strings and legacy files staying strings: OK
- User-supplied default= and cls= kwargs forwarded to json.dumps: default OK, cls broken
- Collision of the reserved tag keys with user data
- CachingMiddleware deferred writes: OK
- Failed serialisation raises before the file is truncated or written, so no data loss
- C4 import layering and C5 stdlib-only: OK
- Query hash and caching with datetime args: unchanged; datetimes are hashable
- Git-dependent tests being brittle in non-git environments

<sub>cost $0.226, 9 turns</sub>
