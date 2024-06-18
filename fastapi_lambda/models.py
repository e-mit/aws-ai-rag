"""Pydantic models for the API."""

from typing import Any
from enum import Enum
from typing_extensions import Self

from pydantic import BaseModel, Field, model_validator


class LLM_RequestQuery(BaseModel):
    """Represents the posted input to the query."""
    query: str


class LLM_Query(LLM_RequestQuery):
    """Represents the input to the RAG-LLM."""
    id: str


class LLM_Response(BaseModel):
    """Represents the LLM response."""
    answer: str
    article_refs: list[Any]


class StatusEnum(str, Enum):
    pending = 'pending'
    completed = 'completed'


class GetStatus(BaseModel):
    """Represents the API response"""
    id: str
    status: StatusEnum = Field(default=StatusEnum.pending, init=False)
    response: LLM_Response | None

    @model_validator(mode='after')
    def check_status(self) -> Self:
        if self.response is not None:
            self.status = StatusEnum.completed
        return self
