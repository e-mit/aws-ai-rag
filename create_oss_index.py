"""Create a k-NN index in the OpenSearch Service database"""
import os

from opensearchpy import OpenSearch, RequestsHttpConnection
import boto3
from requests_aws4auth import AWS4Auth

OSS_NODE_URL = os.environ['OSS_NODE_URL']
AWS_REGION = os.environ['AWS_REGION']
EMBEDDING_DIMENSION = 1024
INDEX_NAME = "news"  # must be lower case

##################################################

SERVICE = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, AWS_REGION,
                   SERVICE, session_token=credentials.token)

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

if index_body['mappings']['properties']['embedding']['method']['engine'] == 'nmslib':
    index_body['settings']['index']['knn.algo_param.ef_search'] = 100

response = client.indices.create(index=INDEX_NAME, body=index_body)
