import sys
import os
import uuid

import pytest

os.environ['AWS_REGION'] = "eu-west-3"
os.environ['OPENSEARCH_URL'] = 'https://search-osstest2-oss-domain-2fgz4fbh4p2z3ul3z7goiutaay.eu-west-3.es.amazonaws.com'

sys.path.append("query_lambda")

from query_lambda import lambda_function, params, database  # noqa


def test_success():
    result = lambda_function.process_query(
        {'query': 'Summarize the UK news yesterday'}, None)
    print(result)  # NB: enable using: pytest -v -s tests
    assert len(result.answer) > 0
    assert isinstance(result.answer, str)
    assert len(result.article_refs) >= 1


def test_inappropriate():
    result = lambda_function.process_query(
        {'query': 'where can i buy pizza?'}, None)
    assert result.answer == params.INAPPROPRIATE_REPLY
    assert len(result.article_refs) == 0


@pytest.mark.skip(reason="TODO")
def test_no_results():
    result = lambda_function.process_query(
        {'query': 'What was the UK news 10 days ago?'}, None)
    assert len(result.article_refs) == 0


def test_lambda_success():
    id = str(uuid.uuid4().int)
    database.add_new(id)
    assert database.get(id) is None
    lambda_function.lambda_handler(
        {'id': id, 'query': 'Summarize the UK news yesterday'}, None)
    result = database.get(id)
    assert result is not None
    assert len(result.answer) > 0
    assert isinstance(result.answer, str)
    assert len(result.article_refs) >= 1


def test_lambda_nonexistent_id():
    id = '19191'
    with pytest.raises(Exception):
        lambda_function.lambda_handler(
            {'id': id, 'query': 'Summarize the UK news yesterday'}, None)
