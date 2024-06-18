"""Query the OpenSearch Service database"""

import datetime
from datetime import timedelta
import json

from opensearchpy import OpenSearch, RequestsHttpConnection
import boto3
from requests_aws4auth import AWS4Auth

NODE_URL = 'https://search-osstest2-oss-domain-2fgz4fbh4p2z3ul3z7goiutaay.eu-west-3.es.amazonaws.com'
INDEX_NAME = "news"  # must be lower case
AWS_REGION = "eu-west-3"

EMBEDDING_MODEL = {'id': "amazon.titan-embed-image-v1", 'dimension': 1024}
embedding_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

##################################################

service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, AWS_REGION,
                   service, session_token=credentials.token)

client = OpenSearch(
        hosts=[NODE_URL],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        http_compress=True,
        connection_class=RequestsHttpConnection
        )


def apply_embedding(input_text: str) -> list[float]:
    response = embedding_client.invoke_model(
        modelId=EMBEDDING_MODEL['id'],
        body=json.dumps({"inputText": input_text}))
    return json.loads(response["body"].read())["embedding"]


##############################

# Example query
user_query = "Ukraine"

query_embedding = apply_embedding(user_query)

query_body = {
    "size": 3,  # Limits number of hits returned
    "query": {"knn": {"embedding": {"vector": query_embedding, "k": 3}}}
}
# "k" is the number of nearest-neighbours found per shard/segment
# "size" acts as an overall limit on the number returned.

results = client.search(
    body=query_body,
    index=INDEX_NAME,
    _source="title,url",
)

print()
print(results)

##############################

# Example query with filtering by date
user_query2 = "Ukraine"

query_embedding2 = apply_embedding(user_query)

time_now = datetime.datetime.now()
query_body2 = {
    "size": 3,  # Limits number of hits returned
    "query": {"knn": {"embedding": {
        "vector": query_embedding2, "k": 3, "filter": {
          "bool": {
            "must": [
              {
                "range": {
                  "time_read": {
                    "gte": (time_now - timedelta(hours=8)).timestamp(),
                    "lte": time_now.timestamp()
                  }
                }
              }
            ]
          }
        }
    }
}}}

# For categorical data, use "term" in place of "range"
# e.g.   {"term": {"size": "small"}}

results2 = client.search(
    body=query_body2,
    index=INDEX_NAME,
    _source="title,url,time_read",
)

print()
print(results2)
