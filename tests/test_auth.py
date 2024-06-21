import sys
from datetime import datetime, timedelta, timezone

import pytest
from passlib.context import CryptContext
from fastapi import HTTPException
from jose import jwt

sys.path.append("fastapi_lambda")

from fastapi_lambda import auth  # noqa


def make_password_hash(password: str) -> str:
    return CryptContext(schemes=['bcrypt'], deprecated='auto').hash(password)


def test_UserDataDict():
    data = auth.UserDataDict()
    assert data.get("bob") is None
    ud = auth.UserData(username="bob", hashed_password="abc",
                       token_expire_mins=5)
    data.add(ud)
    assert data.get("bob") == ud
    ud2 = auth.UserData(username="def gh", hashed_password="a43d2bc",
                        token_expire_mins=1)
    data.add(ud2)
    assert data.get("def gh") == ud2
    assert data.get("bob") == ud
    assert data.get("ggbgbgb") is None


def test_users():
    assert auth.USERS.get("admin") is not None
    assert auth.USERS.get("user") is not None
    assert auth.USERS.get("fvfvfv") is None


@pytest.fixture
def set_passwords():
    auth.USERS._dict[
        'admin'].hashed_password = make_password_hash("admin_password")
    auth.USERS._dict[
        'user'].hashed_password = make_password_hash("user_password")


def test_authenticate_user_unauth(set_passwords):
    assert auth.authenticate_user("jdbhv", "jbjbj") is None
    assert auth.authenticate_user("admin", "jbjbj") is None
    assert auth.authenticate_user("user", "jbjbj") is None
    assert auth.authenticate_user("user", "admin_password") is None


def test_authenticate_user_auth(set_passwords):
    data = auth.authenticate_user("admin", "admin_password")
    assert data is not None
    assert data.username == "admin"
    data = auth.authenticate_user("user", "user_password")
    assert data is not None
    assert data.username == "user"


def test_create_token_auth(set_passwords):
    token = auth.create_token("admin", "admin_password")
    assert isinstance(token, auth.Token)
    assert token.token_type == "bearer"


def test_create_token_unauth(set_passwords):
    with pytest.raises(HTTPException):
        auth.create_token("admin", "fbfbfbfb")


def test_get_current_user_auth(set_passwords):
    token = auth.create_token("admin", "admin_password")
    assert auth.get_current_user(token.access_token) == "admin"


def test_get_current_user_unknown():
    """Valid token but user is unknown."""
    user = auth.UserData(username="bob",
                         hashed_password=make_password_hash("hello"),
                         token_expire_mins=5)
    access_token = auth.create_access_token(user)
    with pytest.raises(HTTPException):
        auth.get_current_user(access_token)


def test_get_current_user_no_user():
    """Valid token but does not contain a user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=3)
    access_token = jwt.encode({"exp": expire}, auth.AUTH_SECRET_KEY,
                              algorithm=auth.ALGORITHM)
    with pytest.raises(HTTPException):
        auth.get_current_user(access_token)


def test_get_current_user_bad_token():
    with pytest.raises(HTTPException):
        auth.get_current_user("kjbhgjhnk")
