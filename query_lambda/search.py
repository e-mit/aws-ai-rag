"""Interface for doing vector similarity searches on Amazon OpenSearch."""

import json
import logging
import os
from typing import Any
from datetime import datetime, date

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth  # type: ignore

from . import params
from .search_models import SearchHit, Source

logger = logging.getLogger()
AWS_REGION = os.environ['AWS_REGION']
OPENSEARCH_URL = os.environ['OPENSEARCH_URL']
OSS_INDEX_NAME = os.getenv('OSS_INDEX_NAME', 'news')

embedding_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
credentials = boto3.Session().get_credentials()
if credentials is None:
    raise PermissionError("Could not get session credentials.")
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, AWS_REGION,
                   'es', session_token=credentials.token)
os_client = OpenSearch(
                hosts=[OPENSEARCH_URL],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                ssl_assert_hostname=False,
                ssl_show_warn=False,
                http_compress=True,
                connection_class=RequestsHttpConnection
            )


def apply_embedding(input_text: str) -> list[float]:
    """Create a vector embedding of the input text."""
    response = embedding_client.invoke_model(
        modelId=params.EMBEDDING_MODEL_ID,
        body=json.dumps({"inputText": input_text}))
    return json.loads(response["body"].read())["embedding"]


class Search:
    """Do a simple vector similarity search."""

    def __init__(self, query: str):
        self.query = query

    def _get_query_body(self) -> dict[str, Any]:
        """Create the search query."""
        return {
            "size": params.QUERY_SIZE,
            "query": {"knn": {"embedding": {
                "vector": apply_embedding(self.query),
                "k": params.QUERY_K}}}
        }

    def run(self) -> list[SearchHit]:
        """Execute the search."""
        results = os_client.search(
            body=self._get_query_body(),
            index=OSS_INDEX_NAME,
            _source=Source.get_attribute_string()  # type: ignore
        )
        if results['timed_out']:
            raise TimeoutError("Search timed out")
        return [SearchHit(**x) for x in results['hits']['hits']]


class DateFilteredSearch(Search):
    """Do a vector similarity search, also filtering by date range."""

    def __init__(self, query: str, start_day: date, end_day: date):
        super().__init__(query)
        self.t1 = datetime.combine(start_day, datetime.min.time())
        self.t2 = datetime.combine(end_day, datetime.max.time())

    def _get_query_body(self) -> dict[str, Any]:
        """Create the search query."""
        date_query_body = super()._get_query_body()
        date_query_body['query']['knn']['embedding']['filter'] = {
            "bool": {
                "must": [{
                    "range": {
                        "time_read": {
                            "gte": self.t1.timestamp(),
                            "lt": self.t2.timestamp()
                        }
                    }
                }]
            }
        }
        return date_query_body
