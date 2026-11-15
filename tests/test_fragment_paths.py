from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage


def test_fragment_on_different_paths_is_not_served_from_cache():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'ana', 'home': {'city': 'Pune'}, 'work': {'city': 'Delhi'}})
    db.insert({'name': 'raj', 'home': {'city': 'Delhi'}, 'work': {'city': 'Pune'}})
    User = Query()
    assert [d['name'] for d in db.search(User.home.fragment({'city': 'Pune'}))] == ['ana']
    assert [d['name'] for d in db.search(User.work.fragment({'city': 'Pune'}))] == ['raj']


def test_fragment_hash_includes_path():
    assert Query().a.fragment({'x': 1}) != Query().b.fragment({'x': 1})
    assert Query().a.fragment({'x': 1}) == Query().a.fragment({'x': 1})
