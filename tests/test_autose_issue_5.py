import ast
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tinydb import Query, TinyDB
from tinydb.storages import JSONStorage, MemoryStorage

ROOT = Path(__file__).resolve().parent.parent


def _roundtrip(tmp_path, *docs, **kwargs):
    path = str(tmp_path / 'db.json')
    db = TinyDB(path, storage=JSONStorage, **kwargs)
    for d in docs:
        db.insert(d)
    db.close()
    return path


def _reopen(path):
    return TinyDB(path, storage=JSONStorage)


def _all(tmp_path, *docs, **kwargs):
    path = _roundtrip(tmp_path, *docs, **kwargs)
    db = _reopen(path)
    try:
        return db.all()
    finally:
        db.close()


def test_fr_json_001_ac_1_naive_datetime_roundtrip(tmp_path):
    orig = datetime(2026, 1, 1, 12, 30, 15, 123456)
    v = _all(tmp_path, {'when': orig})[0]['when']
    assert v == orig
    assert type(v) is datetime
    assert v.tzinfo is None


def test_fr_json_001_ac_2_insert_datetime_no_error(tmp_path):
    path = str(tmp_path / 'new.json')
    db = TinyDB(path, storage=JSONStorage)
    db.insert({'when': datetime(2026, 1, 1, 12, 0)})
    db.close()


def test_fr_json_002_ac_1_date_roundtrip(tmp_path):
    v = _all(tmp_path, {'day': date(2026, 1, 1)})[0]['day']
    assert v == date(2026, 1, 1)
    assert type(v) is date


def test_fr_json_003_ac_1_offset_aware_roundtrip(tmp_path):
    tz = timezone(timedelta(hours=5, minutes=30))
    orig = datetime(2026, 1, 1, 12, 0, tzinfo=tz)
    v = _all(tmp_path, {'when': orig})[0]['when']
    assert v == orig
    assert v.utcoffset() == timedelta(hours=5, minutes=30)
    assert v.tzinfo is not None


def test_fr_json_003_ac_2_utc_roundtrip(tmp_path):
    orig = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    v = _all(tmp_path, {'when': orig})[0]['when']
    assert v.utcoffset() == timedelta(0)
    assert v == orig


def test_fr_json_003_ac_3_naive_and_aware_distinct(tmp_path):
    naive = datetime(2026, 1, 1, 12, 0)
    aware = datetime(2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=-8)))
    docs = _all(tmp_path, {'when': naive}, {'when': aware})
    assert docs[0]['when'].tzinfo is None
    assert docs[1]['when'].utcoffset() == timedelta(hours=-8)


def test_fr_json_004_ac_1_strings_stay_strings(tmp_path):
    doc = {'a': '2026-01-01', 'b': '2026-01-01T12:00:00',
           'c': '2026-01-01T12:00:00+05:30'}
    got = _all(tmp_path, dict(doc))[0]
    for k, text in doc.items():
        assert type(got[k]) is str
        assert got[k] == text


def test_fr_json_004_ac_2_string_and_date_distinguished(tmp_path):
    got = _all(tmp_path, {'s': '2026-01-01', 'd': date(2026, 1, 1)})[0]
    assert type(got['s']) is str
    assert type(got['d']) is date


def test_fr_json_005_ac_1_datetime_less_than_query(tmp_path):
    path = _roundtrip(tmp_path, {'when': datetime(2025, 6, 1, 12, 0)},
                      {'when': datetime(2026, 6, 1, 12, 0)})
    db = _reopen(path)
    res = db.search(Query().when < datetime(2026, 1, 1))
    db.close()
    assert len(res) == 1
    assert res[0]['when'] == datetime(2025, 6, 1, 12, 0)


def test_fr_json_005_ac_2_date_ge_query(tmp_path):
    path = _roundtrip(tmp_path, {'day': date(2025, 6, 1)},
                      {'day': date(2026, 6, 1)})
    db = _reopen(path)
    res = db.search(Query().day >= date(2026, 1, 1))
    db.close()
    assert len(res) == 1
    assert res[0]['day'] == date(2026, 6, 1)


def test_fr_json_005_ac_3_aware_equality_query(tmp_path):
    dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    path = _roundtrip(tmp_path, {'when': dt})
    db = _reopen(path)
    res = db.search(Query().when == dt)
    db.close()
    assert len(res) == 1


def test_con_001_ac_1_no_runtime_dependencies():
    import tomllib
    data = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    assert not data.get('project', {}).get('dependencies')


def test_con_001_ac_2_only_stdlib_imports():
    tree = ast.parse((ROOT / 'tinydb' / 'storages.py').read_text())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            mods.add(node.module.split('.')[0])
    for m in mods:
        assert m in sys.stdlib_module_names or m == 'tinydb', m


def test_con_002_ac_1_memory_storage_keeps_object():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'when': datetime(2026, 1, 1)})
    v = db.all()[0]['when']
    assert v == datetime(2026, 1, 1)
    assert type(v) is datetime


def test_con_002_ac_2_memory_storage_behaviour_unchanged():
    # MemoryStorage stores objects as-is, without any encoding.
    st = MemoryStorage()
    assert st.read() is None
    dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
    data = {'_default': {'1': {'when': dt, 'day': date(2026, 1, 1)}}}
    st.write(data)
    assert st.read() is data
    assert st.read()['_default']['1']['when'] is dt


def test_con_003_ac_1_query_behaviour_on_plain_values():
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'n': 1, 's': 'a'}, {'n': 5, 's': 'b'}])
    assert len(db.search(Query().n > 2)) == 1
    assert len(db.search(Query().s == 'a')) == 1
    assert len(db.search(Query().n.one_of([1, 5]))) == 2


def test_con_003_ac_2_query_public_names_unchanged():
    public = {n for n in dir(Query) if not n.startswith('_')}
    expected = {'is_cacheable', 'exists', 'matches', 'search', 'test', 'any',
                'all', 'one_of', 'fragment', 'noop', 'map'}
    assert public == expected


def test_fr_json_001_ac_1_custom_default_kwarg_still_used(tmp_path):
    got = _all(tmp_path, {'s': {3, 1, 2}, 'when': datetime(2026, 1, 1, 12, 0)},
               default=lambda o: sorted(o))[0]
    assert got['s'] == [1, 2, 3]
    assert got['when'] == datetime(2026, 1, 1, 12, 0)


def test_fr_json_002_ac_1_custom_cls_kwarg_still_used(tmp_path):
    class SetEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, set):
                return sorted(o)
            return super().default(o)

    got = _all(tmp_path, {'s': {3, 1}, 'when': datetime(2026, 1, 1, 12, 0),
                          'day': date(2026, 1, 1)}, cls=SetEncoder)[0]
    assert got['s'] == [1, 3]
    assert got['when'] == datetime(2026, 1, 1, 12, 0)
    assert type(got['day']) is date
