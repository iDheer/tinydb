from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage


def make_db(docs):
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple(docs)
    return db


def err_docs(n_err, n_other=0):
    docs = [{'n': i, 'level': 'error'} for i in range(n_err)]
    docs += [{'n': 100 + i, 'level': 'info'} for i in range(n_other)]
    return docs


def test_fr_search_001_ac_1_limit_truncates():
    db = make_db(err_docs(15, 10))
    table = db.table('_default')
    res = table.search(Query().level == 'error', limit=10)
    assert len(res) == 10
    assert all(d['level'] == 'error' for d in res)


def test_fr_search_001_ac_2_fewer_than_limit():
    db = make_db(err_docs(3, 5))
    res = db.table('_default').search(Query().level == 'error', limit=10)
    assert len(res) == 3
    assert [d['n'] for d in res] == [0, 1, 2]


def test_fr_search_001_ac_3_exactly_limit():
    db = make_db(err_docs(10, 4))
    table = db.table('_default')
    q = Query().level == 'error'
    assert len(table.search(q, limit=10)) == 10


def test_fr_search_001_ac_4_db_forwarding():
    db = make_db(err_docs(15))
    res = db.search(Query().level == 'error', limit=10)
    assert len(res) == 10


def test_fr_search_001_ac_5_cached_then_limit():
    db = make_db(err_docs(15))
    q = Query().level == 'error'
    assert len(db.search(q)) == 15
    assert len(db.search(q, limit=10)) == 10


def test_fr_search_002_ac_1_order_preserved():
    db = make_db([
        {'n': 1, 'level': 'error'},
        {'n': 2, 'level': 'info'},
        {'n': 3, 'level': 'error'},
        {'n': 4, 'level': 'error'},
    ])
    q = Query().level == 'error'
    limited = db.search(q, limit=2)
    assert [d['n'] for d in limited] == [1, 3]
    assert limited == db.search(q)[:2]


def test_fr_search_002_ac_2_doc_ids_order():
    db = make_db(err_docs(12, 3))
    q = Query().level == 'error'
    cold = [d.doc_id for d in db.search(q, limit=5)]
    full = [d.doc_id for d in db.search(q)]
    warm = [d.doc_id for d in db.search(q, limit=5)]
    assert cold == full[:5]
    assert warm == full[:5]


def test_fr_search_003_ac_1_unlimited_all_in_order():
    db = make_db(err_docs(15, 5))
    res = db.search(Query().level == 'error')
    assert len(res) == 15
    assert [d['n'] for d in res] == list(range(15))


def test_fr_search_003_ac_2_fresh_list_each_call():
    db = make_db(err_docs(15))
    q = Query().level == 'error'
    first = db.search(q)
    second = db.search(q)
    assert first == second
    assert first is not second
    second.pop()
    assert len(db.search(q)) == 15


def test_fr_search_003_ac_3_no_match_empty_list():
    db = make_db(err_docs(5))
    res = db.search(Query().level == 'nothing')
    assert res == []
    assert isinstance(res, list)


def test_fr_search_003_ac_4_unlimited_after_limited_not_truncated():
    # Regression guard: a limited search must not poison later unlimited ones.
    db = make_db(err_docs(15))
    q = Query().level == 'error'
    db.search(q, limit=10)
    assert len(db.search(q)) == 15
