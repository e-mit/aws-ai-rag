"""Tests for main.py"""

import sys
from unittest.mock import Mock
from typing import Any

import pytest
from fastapi.testclient import TestClient
from mangum import Mangum

from . import test_auth

sys.path.append("fastapi_lambda")

from fastapi_lambda import database, app_main, models, lambda_function, auth  # noqa

client = TestClient(app_main.app)

app_main.lambda_client = Mock()
attrs: dict[str, Any] = {'invoke.return_value': []}
app_main.lambda_client.configure_mock(**attrs)

URL_BASE_PATH = f"/{app_main.API_STAGE_NAME}/{app_main.PATH_PREFIX}"


@pytest.fixture
def token():
    auth.USERS._dict[
        'admin'].hashed_password = test_auth.make_password_hash(
            "admin_password")
    user = auth.USERS.get("admin")
    assert user is not None
    return auth.create_access_token(user)


def test_get_version():
    response = client.get(f"{URL_BASE_PATH}/version")
    assert response.status_code == 200
    assert response.json() == {
        "api_version": app_main.APIVersion().api_version}


def test_post_query_without_auth():
    body = models.LlmRequestQuery(query="What is the latest news?")
    response = client.post(f"{URL_BASE_PATH}/query", json=body.model_dump())
    assert response.status_code == 401


def test_post_query_fake_auth():
    body = models.LlmRequestQuery(query="What is the latest news?")
    response = client.post(f"{URL_BASE_PATH}/query", json=body.model_dump(),
                           headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 401


def test_post_query_get_empty_response(token):
    app_main.lambda_client.invoke.reset_mock()
    body = models.LlmRequestQuery(query="What is the latest news?")
    response = client.post(f"{URL_BASE_PATH}/query", json=body.model_dump(),
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert 'id' in response.json()
    id = response.json()['id']
    assert isinstance(id, str)
    app_main.lambda_client.invoke.assert_called_once()
    response2 = client.get(f"{URL_BASE_PATH}/query/{id}")
    assert response2.status_code == 200
    data = response2.json()
    assert data['id'] == id
    assert data['status'] == 'pending'
    assert data['response'] is None


def test_post_query_get_response(token):
    app_main.lambda_client.invoke.reset_mock()
    body = models.LlmRequestQuery(query="What is the latest news?")
    response = client.post(f"{URL_BASE_PATH}/query", json=body.model_dump(),
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert 'id' in response.json()
    id = response.json()['id']
    assert isinstance(id, str)
    app_main.lambda_client.invoke.assert_called_once()
    response = database.LlmResponse(answer="the answer",
                                    article_refs=["a", "b"])
    database.update(id, response)
    response2 = client.get(f"{URL_BASE_PATH}/query/{id}")
    assert response2.status_code == 200
    data = response2.json()
    assert data['id'] == id
    assert data['status'] == 'completed'
    assert (database.LlmResponse(
        **data['response']).model_dump_json() == response.model_dump_json())


def test_get_bad_id():
    id = '999'
    response = client.get(f"{URL_BASE_PATH}/query/{id}")
    assert response.status_code == 404


def test_module_load():
    assert isinstance(lambda_function.lambda_handler, Mangum)


def test_token(token):
    response = client.post(f"{URL_BASE_PATH}/token", data={'username': 'admin',
                           'password': 'admin_password'})
    assert response.status_code == 200
    received_token = auth.Token(**response.json())
    assert auth.get_current_user(received_token.access_token) == "admin"
    assert received_token.token_type == "bearer"


def test_get_root():
    response = client.get(f"{URL_BASE_PATH}")
    assert response.status_code == 200
    assert app_main.TITLE in response.text
