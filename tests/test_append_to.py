from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage


def test_append_to_existing_and_missing_list():
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'id': 1, 'tags': ['a']}, {'id': 2}])
    db.append_to('tags', 'x', Query().id.exists())
    assert db.get(doc_id=1)['tags'] == ['a', 'x']
    assert db.get(doc_id=2)['tags'] == ['x']
