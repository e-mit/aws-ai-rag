"""Create a k-NN index in the OpenSearch database (if not already existing)."""

import os
import sys

from opensearchpy import OpenSearch, RequestsHttpConnection
import boto3
from requests_aws4auth import AWS4Auth  # type: ignore

OSS_NODE_URL = os.environ['OSS_NODE_URL']
AWS_REGION = os.environ['AWS_REGION']
OSS_INDEX_NAME = os.environ['OSS_INDEX_NAME']  # must be lower case
EMBEDDING_DIMENSION = 1024

##################################################

SERVICE = 'es'
credentials = boto3.Session().get_credentials()
if credentials is None:
    raise PermissionError("Could not get session credentials.")
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, AWS_REGION,
                   SERVICE, session_token=credentials.token)

try:
    client = OpenSearch(
            hosts=[OSS_NODE_URL],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            http_compress=True,
            connection_class=RequestsHttpConnection
            )
except Exception:
    print("Could not connect to the OpenSearch service.")
    sys.exit(1)

if client.indices.exists(index=OSS_INDEX_NAME):
    print(f"The OSS index '{OSS_INDEX_NAME}' already exists"
          ", so will not be recreated.")
    sys.exit(0)

index_body = {
  "settings": {
    "index": {
      "knn": True
    }
  },
  "mappings": {
    "properties": {
      "embedding": {
        "type": "knn_vector",
        "dimension": EMBEDDING_DIMENSION,
        "method": {
          "name": "hnsw",
          "space_type": "l2",
          "engine": "lucene",  # nmslib, lucene, faiss
          "parameters": {
            "ef_construction": 100,
            "m": 16
          }
        }
      }
    }
  }
}

if index_body['mappings']['properties']['embedding'][  # type: ignore
        'method']['engine'] == 'nmslib':
    index_body['settings']['index'][  # type: ignore
        'knn.algo_param.ef_search'] = 100

response = client.indices.create(index=OSS_INDEX_NAME, body=index_body)

if not (response['acknowledged'] and response['shards_acknowledged']
        and response['index'] == OSS_INDEX_NAME):
    print(f"Error: got response = {response}")
else:
    print(f"Created OSS index {OSS_INDEX_NAME}")

# client.indices.delete(index=OSS_INDEX_NAME)
