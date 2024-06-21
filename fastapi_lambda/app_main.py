"""Create and configure the FastAPI app."""

from typing import Annotated
import logging
import uuid
import os

import boto3
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from fastapi import status, Path
from fastapi import HTTPException
from pydantic import BaseModel

from .models import LlmQuery, LlmRequestQuery, QueryStatus
from . import database
from . import auth

logger = logging.getLogger()

LLM_LAMBDA_ARN = os.environ['LLM_LAMBDA_ARN']
TITLE = "RAG for LLM"
MAX_ID_LENGTH = 39  # This is a 128-bit number

lambda_client = boto3.client('lambda')  # type: ignore


class APIVersion(BaseModel):
    """Provide the version of the API."""

    api_version: str = "0.1.0"


app = FastAPI(
    title=TITLE,
    description="An API for querying an LLM using RAG with news articles.",
    version=f"v{APIVersion().api_version}",
    contact={
        "name": "e-mit.github.io",
        "url": "https://e-mit.github.io/"
    },
    license_info={
        "name": "AGPL-3.0 license",
        "url": "https://www.gnu.org/licenses/agpl-3.0.html#license-text",
    },
    redoc_url=None
)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect to the Swagger UI."""
    return RedirectResponse(url="/docs")


@app.get("/version", tags=["Version"])
async def version() -> APIVersion:
    """Get the API version."""
    return APIVersion()


@app.post("/query", status_code=status.HTTP_201_CREATED)
def post_query(query: LlmRequestQuery,
               _username: auth.AuthenticatedUsername) -> dict[str, str]:
    """Start a new query."""
    _id = str(uuid.uuid4().int)
    database.add_new(_id)
    response = lambda_client.invoke(
        FunctionName=LLM_LAMBDA_ARN,
        InvocationType='Event',
        Payload=LlmQuery(**query.model_dump(), id=_id).model_dump_json()
    )
    if 'FunctionError' in response:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="The LLM service failed")
    return {'id': _id}


@app.get("/query/{query_id}", status_code=status.HTTP_200_OK)
def get_response(query_id: Annotated[str, Path(max_length=MAX_ID_LENGTH)],
                 ) -> QueryStatus:
    """Get the query response using its id."""
    try:
        data = database.get(query_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Query ID does not exist") from e
    return QueryStatus(id=query_id, response=data)


@app.post("/token")
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
        ) -> auth.Token:
    """Authenticate the user and provide a bearer token."""
    return auth.create_token(form_data.username, form_data.password)


@app.get("/who/")
async def who(username: auth.AuthenticatedUsername):
    """Return the username of the authenticated user."""
    return {"username": username}
