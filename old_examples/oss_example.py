"""Create an index, add data, query it, delete the index."""

import json

from opensearchpy import OpenSearch, RequestsHttpConnection
import boto3
from requests_aws4auth import AWS4Auth

NODE_URL = 'https://search-osstest1-domain-cjp2xxkwrxweso53njzwamklxq.eu-west-3.es.amazonaws.com'
INDEX_NAME = "test"  # must be lower case
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
        "dimension": EMBEDDING_MODEL['dimension'],
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

##############################

# The text to convert to an embedding.
input_texts = ["Hi my name is Bob.", "The kitchen needs sugar",
               "Cats and dogs fight."]
ids = [0, 1, 2]
timestamps = [100, 200, 300]

for i, input_text in enumerate(input_texts):
    res = client.index(
        index=INDEX_NAME,
        body={"timestamp": timestamps[i],
              "text": input_text,
              "embedding": apply_embedding(input_text)},
        id=ids[i],
        refresh=True
    )

# test overwriting:
input_texts[1] = "The kitchen needs salt"
res = client.index(
    index=INDEX_NAME,
    body={"timestamp": timestamps[1],
          "text": input_texts[1],
          "embedding": apply_embedding(input_texts[1])},
    id=ids[1],
    refresh=True
)

#####################################################

# Example query
user_query = "Kitchen ingredients"

""" Embedding the query by using the same model """
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
    _source="text",
)

print()
print(results)


for i, result in enumerate(results["hits"]["hits"]):
    id = result['_id']
    score = result['_score']
    print(f"Result{i+1}: ID={id}, Score={score}")


# Delete a single document by its id, then repeat the search
print()
client.delete(index=INDEX_NAME, id=1, refresh=True)
results = client.search(
    body=query_body,
    index=INDEX_NAME,
    _source="false",
)
for i, result in enumerate(results["hits"]["hits"]):
    id = result['_id']
    score = result['_score']
    print(f"Result{i+1}: ID={id}, Score={score}")


# delete documents older than a certain time:
query_body_time = {
    "size": 3,  # Limits number of hits returned
    "query": {"range": {"timestamp": {"lt": 150}}}
}
print()
client.delete_by_query(index=INDEX_NAME, body=query_body_time, refresh=True)
results = client.search(
    body=query_body,
    index=INDEX_NAME,
    _source="false",
)
for i, result in enumerate(results["hits"]["hits"]):
    id = result['_id']
    score = result['_score']
    print(f"Result{i+1}: ID={id}, Score={score}")


# look for matching **_id** value
query_body_match = {
    "size": 2,  # Limits number of hits returned
    "query": {"ids": {"values": [2]}}
}
results = client.search(
    body=query_body_match,
    index=INDEX_NAME,
    _source='false',
)
print()
print(results)

# look for matching timestamp value (ie. a document field, not the _id)
query_body_match2 = {
    "size": 2,  # Limits number of hits returned
    "query": {"match": {"timestamp": 300}}
}
results = client.search(
    body=query_body_match2,
    index=INDEX_NAME,
    _source='false',
)
print()
print(results)

query_body_nomatch = {
    "size": 3,  # Limits number of hits returned
    "query": {"ids": {"values": [99]}}
}
results = client.search(
    body=query_body_nomatch,
    index=INDEX_NAME,
    _source='false',
)
print()
print(results)


client.indices.delete(index=INDEX_NAME)
