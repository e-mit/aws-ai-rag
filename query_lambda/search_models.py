"""Pydantic models for validating search results."""

from typing import Any, Annotated
from abc import ABC, abstractmethod

from pydantic import BaseModel, field_validator, HttpUrl, Field

from . import params


class SourceSummary(BaseModel):
    """Represents part of the selected source data in the search result."""

    time_read: float
    title: str
    url: HttpUrl

    @classmethod
    def get_attribute_string(cls):
        """List what data are required in the search result."""
        return ",".join(cls.model_fields.keys())


class Source(SourceSummary):
    """Represents the selected source data in the search result."""

    chunk: str


class Hit(ABC, BaseModel):
    """Represents an OpenSearch search hit."""

    index: str = Field(alias="_index")
    id: str = Field(alias="_id")
    score: float = Field(alias="_score")

    @field_validator('index')
    @classmethod
    def check_index(cls, v: str) -> str:
        """Validate the search index name."""
        if v != params.INDEX_NAME:
            raise ValueError(f'Unexpected search index: {v}')
        return v

    @abstractmethod
    def get_article_summary(self) -> dict[str, Any]:
        """Get just the brief news-article-related information."""


class SearchHit(Hit):
    """Represents an OpenSearch search hit, with a full record."""

    source: Source = Field(alias="_source")

    def get_article_summary(self) -> dict[str, Any]:
        """Get just the brief news-article-related information."""
        return {k: getattr(self.source, k) for k in
                SourceSummary.model_fields}


class SummarySearchHit(Hit):
    """Represents an OpenSearch search hit, with a summary record."""

    source: Annotated[SourceSummary, Field(alias="_source")]

    def get_article_summary(self) -> dict[str, Any]:
        """Get just the brief news-article-related information."""
        return self.source.model_dump()
