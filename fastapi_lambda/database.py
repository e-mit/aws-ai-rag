import logging
import os
from datetime import datetime, timedelta

import boto3

from models import LLM_Response

DB_TABLE_NAME = os.environ['DB_TABLE_NAME']
TTL_MINUTES = 30
logger = logging.getLogger()

if os.environ.get('TEST'):
    logger.info('Local test mode: using database %s', DB_TABLE_NAME)
    dynamo_table = boto3.resource('dynamodb',
                                  endpoint_url='http://localhost:8000'
                                  ).Table(DB_TABLE_NAME)
else:
    logger.info('Using database %s', DB_TABLE_NAME)
    dynamo_table = boto3.resource('dynamodb').Table(DB_TABLE_NAME)


def get_expiry_timestamp() -> int:
    """The timestamp when the database entry should expire."""
    return int((datetime.now()
                + timedelta(minutes=TTL_MINUTES)).timestamp())


def add_new(id: str) -> None:
    """Store the id in the database."""
    dynamo_table.put_item(
        Item={'id': id, 'expiryTimestamp': get_expiry_timestamp()})


def update(id: str, data: LLM_Response) -> None:
    """Store the data in the database."""
    dynamo_table.put_item(Item={'id': id,
                                'expiryTimestamp': get_expiry_timestamp(),
                                **data.model_dump()})


def get(id: str) -> LLM_Response | None:
    """Get data, or None if pending; raise KeyError if not found."""
    data = dynamo_table.get_item(
            Key={"id": id},
            ProjectionExpression=",".join(LLM_Response.model_fields.keys())
        )
    if 'Item' not in data:
        raise KeyError("ID not found.")
    if not data.get("Item"):
        return None
    return LLM_Response(**data.get("Item"))  # type: ignore
