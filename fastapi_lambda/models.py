"""Pydantic models for the API."""

from typing import Any
from enum import Enum
from typing_extensions import Self

from pydantic import BaseModel, Field, model_validator


class LLM_RequestQuery(BaseModel):
    """Represents the POSTed body input to the API."""
    query: str


class LLM_Query(LLM_RequestQuery):
    """Represents the input to the RAG-LLM lambda."""
    id: str


class LLM_Response(BaseModel):
    """Represents the LLM response as stored in the database."""
    answer: str
    article_refs: list[Any]


class StatusEnum(str, Enum):
    pending = 'pending'
    completed = 'completed'


class QueryStatus(BaseModel):
    """Represents the API response"""
    id: str
    status: StatusEnum = Field(default=StatusEnum.pending, init=False)
    response: LLM_Response | None

    @model_validator(mode='after')
    def check_status(self) -> Self:
        if self.response is not None:
            self.status = StatusEnum.completed
        return self
