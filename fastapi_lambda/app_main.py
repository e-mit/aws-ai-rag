"""Create and configure the FastAPI app."""

from typing import Annotated
import logging
import uuid
import os

import boto3
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi import status, Path
from fastapi import HTTPException
from pydantic import BaseModel

from models import LLM_Query, LLM_RequestQuery, QueryStatus
import database

logger = logging.getLogger()

LLM_LAMBDA_ARN = os.environ['LLM_LAMBDA_ARN']
TITLE = "RAG for LLM"
MAX_ID_LENGTH = 39  # This is a 128-bit number

lambda_client = boto3.client('lambda')


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
def post_query(query: LLM_RequestQuery) -> dict[str, str]:
    """Start a new query."""
    id = str(uuid.uuid4().int)
    database.add_new(id)
    # TODO: add DLQ for failed lambda invocations
    response = lambda_client.invoke(
        FunctionName=LLM_LAMBDA_ARN,
        InvocationType='Event',
        Payload=LLM_Query(**query.model_dump(), id=id).model_dump_json()
    )
    if 'FunctionError' in response:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="The LLM service failed")
    return {'id': id}


@app.get("/query/{id}", status_code=status.HTTP_200_OK)
def get_response(id: Annotated[str, Path(max_length=MAX_ID_LENGTH)]
                 ) -> QueryStatus:
    """Get the query response using its id."""
    try:
        data = database.get(id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Query ID does not exist")
    return QueryStatus(id=id, response=data)
