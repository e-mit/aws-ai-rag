import sys
import os
from datetime import datetime, timedelta

os.environ['AWS_REGION'] = "eu-west-3"

sys.path.append("query_lambda")

from query_lambda import query, search_models, params  # noqa


def test_invoke_llm():
    answer = query.invoke_llm("Hello, who are you?")
    assert isinstance(answer, str)


def test_question_inappropriate():
    assert not query.is_question_appropriate("Hello, who are you?")


def test_question_appropriate():
    assert query.is_question_appropriate("What happened in the USA yesterday?")


def test_get_no_dates():
    assert query.get_relevant_dates("strawberry bicycle") == []


def test_get_no_dates2():
    assert query.get_relevant_dates("What was the UK news 10 days ago?") == []


def test_get_todays_date():
    assert query.get_relevant_dates(
        "What is the news today?") == [datetime.now().date()]


def test_get_date_range():
    result = query.get_relevant_dates(
        "What happened in the last 3 days, including today?")
    assert result is not None
    assert set(result) == set(datetime.now().date()
                              - timedelta(days=x) for x in [0, 1, 2])


def test_create_combined_prompt():
    s1 = search_models.SearchHit(
        _index=params.INDEX_NAME, _id="b", _score=0.5, _source=search_models.Source(
            time_read=1.1, title="title1",
            url="https://hi.com", chunk="this is a test"))
    s2 = search_models.SearchHit(
        _index=params.INDEX_NAME, _id="b", _score=0.5, _source=search_models.Source(
            time_read=1.1, title="title2",
            url="https://example.com", chunk="another test"))
    prompt = query.create_combined_prompt("Give me the news today.", [s1, s2])
    assert "Give me the news today." in prompt
    assert "another test" in prompt
    assert "this is a test" in prompt
