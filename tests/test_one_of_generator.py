from tinydb import Query


def test_one_of_accepts_a_generator():
    query = Query().tag.one_of(t for t in ['a', 'b'])
    assert query({'tag': 'b'})


def test_one_of_with_list_unchanged():
    query = Query().tag.one_of(['a', 'b'])
    assert query({'tag': 'a'}) and not query({'tag': 'c'})
