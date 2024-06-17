"""Pydantic models for validating search results."""

from typing import Any

from pydantic import BaseModel, field_validator, HttpUrl

import params


class SourceSummary(BaseModel):
    """Represents part of the selected source data in the search result."""
    time_read: float
    title: str
    url: HttpUrl


class Source(SourceSummary):
    """Represents the selected source data in the search result."""
    chunk: str

    @classmethod
    def get_attribute_string(cls):
        """List what data are required in the search result."""
        return ",".join(cls.model_fields.keys())


class SearchHit(BaseModel):
    """Represents an OpenSearch search hit."""
    index: str
    _id: str
    _score: float
    _source: Source

    @field_validator('index')
    @classmethod
    def check_index(cls, v: str) -> str:
        """Validate the search index name."""
        if v != params.INDEX_NAME:
            raise ValueError(f'Unexpected search index: {v}')
        return v

    def get_article_summary(self) -> dict[str, Any]:
        return {k: getattr(self._source, k) for k in
                SourceSummary.model_fields.keys()}
