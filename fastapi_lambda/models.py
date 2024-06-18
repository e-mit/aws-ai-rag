"""Pydantic models for the API."""

from enum import Enum
from typing_extensions import Self

from pydantic import BaseModel, Field, model_validator

from . import database


class LlmRequestQuery(BaseModel):
    """Represents the POSTed body input to the API."""

    query: str


class LlmQuery(LlmRequestQuery):
    """Represents the input to the RAG-LLM lambda."""

    id: str


class StatusEnum(str, Enum):
    """Status of the query to the LLM."""

    PENDING = 'pending'
    COMPLETED = 'completed'


class QueryStatus(BaseModel):
    """Represents the API response."""

    id: str
    status: StatusEnum = Field(default=StatusEnum.PENDING, init=False)
    response: database.LlmResponse | None

    @model_validator(mode='after')
    def check_status(self) -> Self:
        """Use the presence of a response to determine the status."""
        if self.response is not None:
            self.status = StatusEnum.COMPLETED
        return self
