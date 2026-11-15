from tinydb import TinyDB, where, Query
from tinydb.storages import MemoryStorage


def _db(*docs):
    db = TinyDB(storage=MemoryStorage)
    for d in docs:
        db.insert(d)
    return db


def test_fr_ops_002_ac_1_append_creates_missing_field():
    from tinydb.operations import append
    db = _db({'id': 7})
    db.update(append('tags', 'urgent'), Query().id == 7)
    assert db.get(Query().id == 7)['tags'] == ['urgent']


def test_fr_ops_002_ac_2_other_documents_untouched():
    from tinydb.operations import append
    db = _db({'id': 7}, {'id': 8})
    db.update(append('tags', 'urgent'), Query().id == 7)
    assert db.get(Query().id == 7)['tags'] == ['urgent']
    assert 'tags' not in db.get(Query().id == 8)


def test_fr_ops_002_ac_3_mixed_existing_and_missing():
    from tinydb.operations import append
    db = _db({'id': 7}, {'id': 8, 'tags': ['a']})
    db.update(append('tags', 'urgent'), Query().id.exists())
    assert db.get(Query().id == 7)['tags'] == ['urgent']
    assert db.get(Query().id == 8)['tags'] == ['a', 'urgent']
