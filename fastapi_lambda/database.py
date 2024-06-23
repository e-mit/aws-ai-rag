"""Database interface for storing query results in dynamoDB."""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import boto3
from pydantic import BaseModel

DB_TABLE_NAME = os.environ['DB_TABLE_NAME']
AWS_REGION = os.environ['AWS_REGION']
TTL_MINUTES = 30
logger = logging.getLogger()


class LlmResponse(BaseModel):
    """Represents the LLM response as stored in the database."""

    answer: str
    article_refs: list[Any]


if os.environ.get('TEST'):
    logger.info('Local test mode: using database %s', DB_TABLE_NAME)
    dynamo_table = boto3.resource('dynamodb',
                                  endpoint_url='http://localhost:8000',
                                  region_name=AWS_REGION
                                  ).Table(DB_TABLE_NAME)
else:
    logger.info('Using database %s', DB_TABLE_NAME)
    dynamo_table = boto3.resource('dynamodb',
                                  region_name=AWS_REGION).Table(DB_TABLE_NAME)


def get_expiry_timestamp() -> int:
    """Get timestamp for when the database entry should expire."""
    return int((datetime.now()
                + timedelta(minutes=TTL_MINUTES)).timestamp())


def add_new(_id: str) -> None:
    """Store the id in the database, without replacement."""
    dynamo_table.put_item(
        Item={'id': _id, 'expiryTimestamp': get_expiry_timestamp()},
        ConditionExpression='attribute_not_exists(id)')


def update(_id: str, data: LlmResponse) -> None:
    """Store the data in the database, replacing previous record."""
    dynamo_table.put_item(Item={'id': _id,
                                'expiryTimestamp': get_expiry_timestamp(),
                                'reply': data.model_dump_json()},
                          ConditionExpression='attribute_exists(id)')


def get(_id: str) -> LlmResponse | None:
    """Get data, or None if pending; raise KeyError if not found."""
    data = dynamo_table.get_item(Key={"id": _id},
                                 ProjectionExpression='reply')
    if 'Item' not in data:
        raise KeyError("ID not found.")
    if not data.get("Item"):
        return None
    return LlmResponse.model_validate_json(
        data.get("Item")['reply'])  # type: ignore
