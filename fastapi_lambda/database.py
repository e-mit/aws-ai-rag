import logging
import os

import boto3

from models import LLM_Response

DB_TABLE_NAME = os.environ['DB_TABLE_NAME']
logger = logging.getLogger()

if os.environ.get('TEST'):
    logger.info('Local test mode: using database %s', DB_TABLE_NAME)
    dynamo_table = boto3.resource('dynamodb',
                                  endpoint_url='http://localhost:8000'
                                  ).Table(DB_TABLE_NAME)
else:
    logger.info('Using database %s', DB_TABLE_NAME)
    dynamo_table = boto3.resource('dynamodb').Table(DB_TABLE_NAME)


def add_new(id: str):
    """Store the id in the database."""
    dynamo_table.put_item(Item={"pk": id})


def get(id: str) -> LLM_Response | None:
    """Get data using the id."""
    data = dynamo_table.get_item(Key={"pk": id}).get("Item", None)
    if data is None:
        return None
    return LLM_Response(**data)  # type: ignore
