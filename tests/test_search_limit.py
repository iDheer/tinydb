from tinydb import TinyDB, where
from tinydb.storages import MemoryStorage


def _db():
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'level': 'error'}, {'level': 'info'}, {'level': 'error'}, {'level': 'error'}])
    return db


def test_search_limit_returns_first_matches_in_order():
    assert [d.doc_id for d in _db().search(where('level') == 'error', limit=2)] == [1, 3]


def test_limited_search_does_not_truncate_later_full_search():
    db = _db()
    q = where('level') == 'error'
    assert len(db.search(q, limit=1)) == 1
    assert [d.doc_id for d in db.search(q)] == [1, 3, 4]
    assert [d.doc_id for d in db.search(q, limit=2)] == [1, 3]
