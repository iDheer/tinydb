from tinydb import TinyDB, where, Query
from tinydb.storages import MemoryStorage

A = {'name': 'ana', 'home': {'city': 'Pune'}, 'work': {'city': 'Delhi'}}
B = {'name': 'raj', 'home': {'city': 'Delhi'}, 'work': {'city': 'Pune'}}
User = Query()


def make_db():
    db = TinyDB(storage=MemoryStorage)
    db.insert(dict(A))
    db.insert(dict(B))
    return db


def home():
    return User.home.fragment({'city': 'Pune'})


def work():
    return User.work.fragment({'city': 'Pune'})


def test_fr_qry_001_ac_1_work_after_home_search():
    db = make_db()
    db.search(home())
    result = db.search(work())
    assert isinstance(result, list)
    assert result == [B]
    assert A not in result


def test_fr_qry_001_ac_2_first_home_search():
    db = make_db()
    result = db.search(home())
    assert isinstance(result, list)
    assert result == [A]


def test_fr_qry_001_ac_3_home_after_work_search():
    db = make_db()
    assert db.search(work()) == [B]
    result = db.search(home())
    assert isinstance(result, list)
    assert result == [A]
    assert B not in result


def test_fr_qry_001_ac_4_home_repeated():
    db = make_db()
    db.search(home())
    db.search(work())
    result = db.search(home())
    assert isinstance(result, list)
    assert result == [A]
