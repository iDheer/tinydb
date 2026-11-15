from tinydb import TinyDB, where
from tinydb.storages import MemoryStorage


def test_search_limit_returns_first_matches():
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'level': 'error'}, {'level': 'info'}, {'level': 'error'}, {'level': 'error'}])
    assert [d.doc_id for d in db.search(where('level') == 'error', limit=2)] == [1, 3]


def test_search_without_limit_returns_all():
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'level': 'error'}, {'level': 'error'}])
    assert len(db.search(where('level') == 'error')) == 2
