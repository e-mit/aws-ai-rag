"""Tests for main.py"""

import sys
from unittest.mock import Mock
from typing import Any

from fastapi.testclient import TestClient

sys.path.append("fastapi_lambda")

from fastapi_lambda import database, app_main, models  # noqa

client = TestClient(app_main.app)

app_main.lambda_client = Mock()
attrs: dict[str, Any] = {'invoke.return_value': []}
app_main.lambda_client.configure_mock(**attrs)


def test_get_version():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {
        "api_version": app_main.APIVersion().api_version}


def test_post_query_get_empty_response():
    app_main.lambda_client.invoke.reset_mock()
    body = models.LlmRequestQuery(query="What is the latest news?")
    response = client.post("/query", json=body.model_dump())
    assert response.status_code == 201
    assert 'id' in response.json()
    id = response.json()['id']
    assert isinstance(id, str)
    app_main.lambda_client.invoke.assert_called_once()
    response2 = client.get(f"/query/{id}")
    assert response2.status_code == 200
    data = response2.json()
    assert data['id'] == id
    assert data['status'] == 'pending'
    assert data['response'] is None


def test_post_query_get_response():
    app_main.lambda_client.invoke.reset_mock()
    body = models.LlmRequestQuery(query="What is the latest news?")
    response = client.post("/query", json=body.model_dump())
    assert response.status_code == 201
    assert 'id' in response.json()
    id = response.json()['id']
    assert isinstance(id, str)
    app_main.lambda_client.invoke.assert_called_once()
    response = database.LlmResponse(answer="the answer",
                                     article_refs=["a", "b"])
    database.update(id, response)
    response2 = client.get(f"/query/{id}")
    assert response2.status_code == 200
    data = response2.json()
    assert data['id'] == id
    assert data['status'] == 'completed'
    assert (database.LlmResponse(
        **data['response']).model_dump_json() == response.model_dump_json())


def test_get_bad_id():
    id = '999'
    response = client.get(f"/query/{id}")
    assert response.status_code == 404
