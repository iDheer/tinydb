from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage


def _db(docs):
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple(docs)
    return db


def test_fr_query_001_ac_1_generator_search():
    db = _db([{'tag': 'a'}, {'tag': 'b'}, {'tag': 'a'}, {'tag': 'c'}])
    allowed = (t for t in ['a', 'b'])
    assert db.search(Query().tag.one_of(allowed)) == [
        {'tag': 'a'}, {'tag': 'b'}, {'tag': 'a'}]


def test_fr_query_001_ac_2_generator_repeated_calls():
    q = Query().key1.one_of(v for v in ['value 1', 'value 2'])
    assert q({'key1': 'value 1'}) is True
    assert q({'key1': 'value 2'}) is True
    assert q({'key1': 'value 1'}) is True


def test_fr_query_001_ac_3_generator_no_match():
    q = Query().key1.one_of(v for v in ['value 1', 'value 2'])
    assert q({'key1': 'value 3'}) is False


def test_fr_query_001_ac_4_generator_order_irrelevant():
    db = _db([{'tag': 'b'}, {'tag': 'a'}, {'tag': 'a'}])

    def gen():
        yield 'a'
        yield 'b'

    assert db.search(Query().tag.one_of(gen())) == [
        {'tag': 'b'}, {'tag': 'a'}, {'tag': 'a'}]


def test_fr_query_002_ac_1_list_direct_calls():
    q = Query().key1.one_of(['value 1', 'value 2'])
    assert q({'key1': 'value 1'}) is True
    assert q({'key1': 'value 2'}) is True
    assert q({'key1': 'value 3'}) is False


def test_fr_query_002_ac_2_list_search():
    db = _db([{'tag': 'a'}, {'tag': 'b'}, {'tag': 'a'}, {'tag': 'c'}])
    assert db.search(Query().tag.one_of(['a', 'b'])) == [
        {'tag': 'a'}, {'tag': 'b'}, {'tag': 'a'}]
