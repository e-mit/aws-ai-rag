
import json
from typing import Any
import datetime
from datetime import timedelta

import boto3
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

NODE_URL = 'https://search-osstest2-oss-domain-2fgz4fbh4p2z3ul3z7goiutaay.eu-west-3.es.amazonaws.com'
INDEX_NAME = "news"  # must be lower case
AWS_REGION = "eu-west-3"

LLM_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

query = 'What has happened in France since 7th June?'

QUERY_SIZE = 3
QUERY_K = 3

#################################

EMBEDDING_MODEL = {'id': "amazon.titan-embed-image-v1", 'dimension': 1024}
embedding_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
SERVICE = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, AWS_REGION,
                   SERVICE, session_token=credentials.token)

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

llm_client = boto3.client("bedrock-runtime", region_name="eu-west-3")

#################################

def invoke(prompt: str):
    native_request: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "top_p": 0.999,
        "top_k": 250
    }

    try:
        response = llm_client.invoke_model(modelId=LLM_MODEL_ID,
                                           body=json.dumps(native_request))
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{LLM_MODEL_ID}'. Reason: {e}")
        exit(1)
    return json.loads(response["body"].read())


today = datetime.datetime.now().strftime('%d %B %Y')
date_prompt = (f"Today is {today}. Given the following query, what"
               " date or dates are relevant when searching a database"
               " of news articles? Return the date(s), as a Python"
               " list of strings, without any other text."
               " Return 'null', not in a list, if no dates are relevant."
               f" Query: '{query}'")

model_response = invoke(date_prompt)
response_text = model_response["content"][0]["text"]
dates = json.loads(response_text.replace("'", '"'))

###########################################


def apply_embedding(input_text: str) -> list[float]:
    response = embedding_client.invoke_model(
        modelId=EMBEDDING_MODEL['id'],
        body=json.dumps({"inputText": input_text}))
    return json.loads(response["body"].read())["embedding"]


# query with filtering by date

query_embedding = apply_embedding(query)
query_body = {
    "size": QUERY_SIZE,
    "query": {"knn": {"embedding": {"vector": query_embedding, "k": QUERY_K}}}
}

if dates is None:
    results = client.search(
        body=query_body,
        index=INDEX_NAME,
        _source="title,url,time_read,full_text",
    )
    hits = results['hits']['hits']
else:
    all_hits = []
    all_scores = []
    for d in dates:
        date_query_body = query_body
        day_start = datetime.datetime.strptime(str(d), "%Y-%m-%d")
        day_end = day_start + timedelta(days=1)
        date_query_body['query']['knn']['embedding']['filter'] = {
            "bool": {
                "must": [{
                    "range": {
                        "time_read": {
                            "gte": day_start.timestamp(),
                            "lte": day_end.timestamp()
                        }
                    }
                }]
            }
        }

        results = client.search(
            body=date_query_body,
            index=INDEX_NAME,
            _source="title,url,time_read,full_text",
        )

        print(f"Date: {d} had {len(results['hits']['hits'])} hits.")

        # check times:
        for hit in results['hits']['hits']:
            time_read = hit['_source']['time_read']
            ok = ((time_read >= day_start.timestamp())
                  and (time_read <= day_end.timestamp()))
            if not ok:
                print(f"NOT in time range: {hit['_source']['title']}")

        all_hits.extend(results['hits']['hits'])

    # Select the best hits:
    all_hits.sort(key=lambda h: h['_score'], reverse=True)
    hits = all_hits[0:QUERY_SIZE]

###################################################

if not hits:
    print("ANSWER: Sorry, I couldn't find any relevant news articles.")
else:
    combined_prompt = f"Today is {today}.\n\n" + "\n\n".join(
        "BBC news article from"
        f" {datetime.datetime.fromtimestamp(x['_source']['time_read']).strftime('%d %B %Y')}."
        f"\n{x['_source']['full_text']}" for x in hits) + f"\n\nToday is {today}. {query}"

    model_response = invoke(combined_prompt)
    print(f"ANSWER: {model_response['content'][0]['text']}")
    print()
    print("This answer accessed the following source news articles:")
    for hit in hits:
        print(f"  '{hit['_source']['title']}' {hit['_source']['url']}")
