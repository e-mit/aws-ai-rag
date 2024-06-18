import sys
import uuid

import pytest

sys.path.append("fastapi_lambda")

from fastapi_lambda import database, models  # noqa


def test_add_bad():
    with pytest.raises(Exception):
        database.add_new(None)  # type: ignore


def test_get_nonexistent():
    with pytest.raises(Exception):
        database.get("12345")


def test_add_twice():
    id = str(uuid.uuid4().int)
    database.add_new(id)
    with pytest.raises(Exception):
        database.add_new(id)


def test_get_pending():
    id1 = str(uuid.uuid4().int)
    database.add_new(id1)
    assert database.get(id1) is None
    id2 = str(uuid.uuid4().int)
    database.add_new(id2)
    assert database.get(id2) is None


def test_get_completed():
    id1 = str(uuid.uuid4().int)
    database.add_new(id1)
    assert database.get(id1) is None
    data = database.LLM_Response(answer="this is the answer",
                                 article_refs=["ref1", "ref2"])
    database.update(id1, data)
    get_data = database.get(id1)
    assert get_data is not None
    assert data.model_dump_json() == get_data.model_dump_json()


def test_update_nonexistent():
    data = database.LLM_Response(answer="this is the answer",
                                 article_refs=["ref1", "ref2"])
    with pytest.raises(Exception):
        database.update('876543', data)
