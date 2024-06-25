"""Functions for authentication with Oauth2 and JWT."""

from typing import Annotated
from datetime import datetime, timedelta, timezone
import os
from dataclasses import dataclass

from fastapi import status, HTTPException
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt
import bcrypt


AUTH_SECRET_KEY = os.environ['AUTH_SECRET_KEY']
ALGORITHM = "HS256"
AUTH_TOKEN_EXPIRE_MINS = int(os.environ.get('AUTH_TOKEN_EXPIRE_MINS', '3'))
AUTH_USER_PASSWORD_HASH = os.environ['AUTH_USER_PASSWORD_HASH']
AUTH_ADMIN_PASSWORD_HASH = os.environ['AUTH_ADMIN_PASSWORD_HASH']
ADMIN_TOKEN_EXPIRE_MINS = 30
CAPTCHA_USERNAME = "captcha"


@dataclass
class UserData:
    """Basic user data."""

    username: str
    hashed_password: str
    token_expire_mins: int


class UserDataDict:
    """Collection of user data."""

    def __init__(self) -> None:
        self._dict: dict[str, UserData] = {}

    def add(self, data: UserData) -> None:
        """Add to the users."""
        if data.username in self._dict:
            raise ValueError("Username already exists.")
        self._dict[data.username] = data

    def get(self, username: str) -> UserData | None:
        """Get user."""
        if username not in self._dict:
            return None
        return self._dict[username]


USERS = UserDataDict()
USERS.add(UserData(username="user", hashed_password=AUTH_USER_PASSWORD_HASH,
                   token_expire_mins=AUTH_TOKEN_EXPIRE_MINS))
USERS.add(UserData(username="admin", hashed_password=AUTH_ADMIN_PASSWORD_HASH,
                   token_expire_mins=ADMIN_TOKEN_EXPIRE_MINS))
USERS.add(UserData(username=CAPTCHA_USERNAME, hashed_password="",
                   token_expire_mins=AUTH_TOKEN_EXPIRE_MINS))
Oauth2Dependency = Annotated[str,
                             Depends(OAuth2PasswordBearer(tokenUrl="token"))]


class Token(BaseModel):
    """Contains the bearer token and type."""

    access_token: str
    token_type: str


def authenticate_user(username: str, password: str) -> UserData | None:
    """Check that the user exists and the password is correct."""
    user = USERS.get(username)
    if (user is not None and
            bcrypt.checkpw(password.encode('utf-8'),
                           user.hashed_password.encode('utf-8'))):
        return user
    return None


def create_access_token(userdata: UserData) -> str:
    """Encode the username and expiry time as a JWT."""
    expire = (datetime.now(timezone.utc)
              + timedelta(minutes=userdata.token_expire_mins))
    data = {"sub": userdata.username, "exp": expire}
    return jwt.encode(data, AUTH_SECRET_KEY, algorithm=ALGORITHM)


def create_token(username: str, password: str) -> Token:
    """Authenticate the user and create a JWT."""
    user = authenticate_user(username, password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(user)
    return Token(access_token=access_token, token_type="bearer")  # nosec


def create_captcha_token() -> Token:
    """Create a JWT in response to a valid captcha."""
    user = USERS.get(CAPTCHA_USERNAME)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user),   # nosec
                 token_type="bearer")


def get_current_user(token: Oauth2Dependency) -> str:
    """Validate the token, then return the username."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e
    user = USERS.get(username)
    if user is None:
        raise credentials_exception
    return user.username


# Create a dependency type
AuthenticatedUsername = Annotated[str, Depends(get_current_user)]
