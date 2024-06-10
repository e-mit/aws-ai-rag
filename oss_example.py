import json

from opensearchpy import OpenSearch, RequestsHttpConnection
import boto3
from requests_aws4auth import AWS4Auth

CLUSTER_URL = 'https://search-osstest1-domain-cjp2xxkwrxweso53njzwamklxq.eu-west-3.es.amazonaws.com'
EMBEDDING_DIMENSION = 1024
INDEX_NAME = "test"  # must be lower case
AWS_REGION = "eu-west-3"

embedding_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
embedding_model_id = "amazon.titan-embed-image-v1"

##################################################

service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, AWS_REGION,
                   service, session_token=credentials.token)

client = OpenSearch(
        hosts=[CLUSTER_URL],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        connection_class=RequestsHttpConnection
        )


def apply_embedding(input_text: str) -> list[float]:
    response = embedding_client.invoke_model(
        modelId=embedding_model_id, body=json.dumps({"inputText": input_text}))
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

##############################

# The text to convert to an embedding.
input_texts = ["Hi my name is Bob.", "The kitchen needs sugar",
               "Cats and dogs fight."]
ids = [0, 1, 2]
timestamps = [100, 200, 300]

for i, input_text in enumerate(input_texts):
    res = client.index(
        index=INDEX_NAME,
        body={"id": ids[i], "timestamp": timestamps[i],
              "embedding": apply_embedding(input_text)},
        id=ids[i],
        refresh=True
    )

#####################################################

# Example query
user_query = "Kitchen ingredients"

""" Embedding the query by using the same model """
query_embedding = apply_embedding(user_query)


query_body = {
    "size": 3,  # Limits number of hits returned
    "query": {"knn": {"embedding": {"vector": query_embedding, "k": 10}}}
}

results = client.search(
    body=query_body,
    index=INDEX_NAME,
    _source="id",
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
    _source="id",
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
    _source="id",
)
for i, result in enumerate(results["hits"]["hits"]):
    id = result['_id']
    score = result['_score']
    print(f"Result{i+1}: ID={id}, Score={score}")


client.indices.delete(index=INDEX_NAME)
