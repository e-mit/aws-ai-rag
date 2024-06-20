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
from passlib.context import CryptContext


AUTH_SECRET_KEY = os.environ['AUTH_SECRET_KEY']
ALGORITHM = "HS256"
AUTH_TOKEN_EXPIRE_MINS = int(os.environ.get('AUTH_TOKEN_EXPIRE_MINS', '5'))
AUTH_USER_PASSWORD_HASH = os.environ['AUTH_USER_PASSWORD_HASH']
AUTH_ADMIN_PASSWORD_HASH = os.environ['AUTH_ADMIN_PASSWORD_HASH']
ADMIN_TOKEN_EXPIRE_MINS = 30


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
Oauth2_dependency = Annotated[str,
                              Depends(OAuth2PasswordBearer(tokenUrl="token"))]
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    """Contains the bearer token and type."""
    access_token: str
    token_type: str


def authenticate_user(username: str, password: str) -> UserData | None:
    """Check that the user exists and the password is correct."""
    user = USERS.get(username)
    if (user is not None and
            password_context.verify(password, user.hashed_password)):
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
    return Token(access_token=access_token, token_type="bearer")


def get_current_user(token: Oauth2_dependency) -> str:
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
    except JWTError:
        raise credentials_exception
    user = USERS.get(username)
    if user is None:
        raise credentials_exception
    return user.username


# Create a dependency type
authenticated_username = Annotated[str, Depends(get_current_user)]