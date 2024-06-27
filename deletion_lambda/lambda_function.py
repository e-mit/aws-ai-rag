"""An AWS Lambda to delete old items from an OpenSearch database."""

import logging
import os
from typing import Any
import datetime
from datetime import timedelta

from opensearchpy import OpenSearch, RequestsHttpConnection
import boto3
from requests_aws4auth import AWS4Auth  # type: ignore

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'DEBUG'))

OPENSEARCH_URL = os.getenv('OPENSEARCH_URL', "https://example.com")
if OPENSEARCH_URL[0:4] != 'http':
    OPENSEARCH_URL = 'https://' + OPENSEARCH_URL
AWS_REGION = os.getenv('AWS_REGION', "eu-west-3")
MAXIMUM_DELETE_BATCH_SIZE = int(os.getenv('MAXIMUM_DELETE_BATCH_SIZE', '100'))
DOCUMENT_EXPIRY_TIME_DAYS = int(os.getenv('DOCUMENT_EXPIRY_TIME_DAYS', '8'))
INDEX_NAME = "news"
SERVICE = 'es'

credentials = boto3.Session().get_credentials()
if credentials is None:
    raise PermissionError("Could not get session credentials.")
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, AWS_REGION,
                   SERVICE, session_token=credentials.token)

oss_client = OpenSearch(
        hosts=[OPENSEARCH_URL],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        http_compress=True,
        connection_class=RequestsHttpConnection
        )


def delete_old_documents(client: OpenSearch, index: str,
                         expiry_time_days: int) -> None:
    """Delete all expired documents from the database."""
    expiry_timestamp = (datetime.datetime.now()
                        - timedelta(days=expiry_time_days)).timestamp()
    query_body_time = {
        "size": MAXIMUM_DELETE_BATCH_SIZE,
        "query": {"range": {"time_read": {"lt": expiry_timestamp}}}
    }
    info = client.delete_by_query(index=index, body=query_body_time,
                                  refresh=True)  # type: ignore
    logger.info('Deleted %s documents', info['deleted'])
    logger.debug('Delete returned: %s', info)


def lambda_handler(event: Any, _context_unused: Any) -> None:
    """Define the lambda function."""
    logger.debug('Event: %s', event)
    delete_old_documents(oss_client, INDEX_NAME, DOCUMENT_EXPIRY_TIME_DAYS)
