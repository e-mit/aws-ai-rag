
import json
from typing import Any
import datetime
from datetime import timedelta
import time
import sys

import boto3
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

NODE_URL = 'https://search-osstest2-oss-domain-2fgz4fbh4p2z3ul3z7goiutaay.eu-west-3.es.amazonaws.com'
INDEX_NAME = "news"  # must be lower case
AWS_REGION = "eu-west-3"

query = 'what has happened in malawi?'

# Search result selection parameters:
QUERY_SIZE = 3
QUERY_K = 3
SCORE_THRESHOLD = 0.1

# LLM parameters:
LLM_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
TEMPERATURE = 0.5
TOP_P = 0.999
TOP_K = 250
MAX_OUTPUT_TOKENS = 1000
TEXT_INPUT_FIELD = 'chunk'  # e.g. 'chunk' or 'full_text'

#################################

print()
print(f"QUESTION: {query}")

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


def invoke(prompt: str):
    native_request: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_OUTPUT_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "top_k": TOP_K
    }

    try:
        response = llm_client.invoke_model(modelId=LLM_MODEL_ID,
                                           body=json.dumps(native_request))
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{LLM_MODEL_ID}'. Reason: {e}")
        sys.exit()
    return json.loads(response["body"].read())


def apply_embedding(input_text: str) -> list[float]:
    response = embedding_client.invoke_model(
        modelId=EMBEDDING_MODEL['id'],
        body=json.dumps({"inputText": input_text}))
    return json.loads(response["body"].read())["embedding"]


#################################
# Identify inappropriate questions
ok_prompt = (f"Does the following query relate to the news? Answer yes or no."
             f" Do not return any other text. Query: '{query}'")
ok_response = invoke(ok_prompt)
ok_text: str = ok_response["content"][0]["text"]

if ok_text.lower() != "yes":
    print("ANSWER: Please ask a question which relates to the news.")
    sys.exit()

###########################################
# Identify relevant dates

today = datetime.datetime.now().strftime('%d %B %Y')
date_prompt = (f"Today is {today}. Given the following query, what"
               " date or dates are relevant when searching a database"
               " of news articles? Return the date(s), as a Python"
               " list of strings, or"
               " return 'null' if no dates are relevant."
               " Do not return any other text."
               f" Query: '{query}'")

date_response = invoke(date_prompt)
date_text = date_response["content"][0]["text"]
dates = json.loads(date_text.replace("'", '"'))

if not dates or dates == ['null']:
    dates = []

print()
print(f"Found {len(dates)} relevant dates.")

###########################################
# Query the database, while also filtering by date (if applicable)

query_body = {
    "size": QUERY_SIZE,
    "query": {"knn": {"embedding": {
        "vector": apply_embedding(query), "k": QUERY_K}}}
}

rejected_hits = []
if not dates:
    results = client.search(
        body=query_body,
        index=INDEX_NAME,
        _source=f"title,url,time_read,{TEXT_INPUT_FIELD}",
    )
    hits = results['hits']['hits']
    print(f"Found {len(hits)} hits with scores of:"
          f" {', '.join(str(h['_score']) for h in hits)}")
else:
    all_hits = []
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
                            "lt": day_end.timestamp()
                        }
                    }
                }]
            }
        }

        results = client.search(
            body=date_query_body,
            index=INDEX_NAME,
            _source=f"title,url,time_read,{TEXT_INPUT_FIELD}",
        )

        print(f"Date: {d} had {len(results['hits']['hits'])} hits, with scores of:"
              f" {', '.join(str(h['_score']) for h in results['hits']['hits'])}")

        # check times:
        for hit in results['hits']['hits']:
            time_read = hit['_source']['time_read']
            ok = ((time_read >= day_start.timestamp())
                  and (time_read < day_end.timestamp()))
            if not ok:
                print(f"Error: not in time range: {hit['_source']['title']}")

        all_hits.extend(results['hits']['hits'])

    # Select the best hits:
    all_hits.sort(key=lambda h: h['_score'], reverse=True)
    n_to_keep = QUERY_SIZE * len(dates)
    hits = all_hits[0:n_to_keep]
    rejected_hits.extend(all_hits[n_to_keep:])

###################################################


def print_hit(hit):
    print(f"  Score: {hit['_score']:.4f}")
    print(f"  Date: {datetime.datetime.fromtimestamp(hit['_source']['time_read']).strftime('%d %B %Y')}")
    print(f"  Title: {hit['_source']['title']}")
    print(f"  Link: {hit['_source']['url']}")


hits = [x for x in hits if x['_score'] >= SCORE_THRESHOLD]
rejected_hits.extend([x for x in hits if x['_score'] < SCORE_THRESHOLD])
print(f"After thresholding, have {len(hits)} hits, with scores of:"
      f" {', '.join(str(h['_score']) for h in hits)}")
print()

if not hits:
    print("ANSWER: Sorry, I couldn't find any relevant news articles.")
    sys.exit()
else:
    combined_prompt = f"Today is {today}.\n\n" + "\n\n".join(
        "Summarized BBC news article from"
        f" {datetime.datetime.fromtimestamp(x['_source']['time_read']).strftime('%d %B %Y')}."
        f"\n{x['_source'][TEXT_INPUT_FIELD]}" for x in hits) + f"\n\nToday is {today}. {query}"

    timer_start = time.perf_counter()
    model_response = invoke(combined_prompt)
    print(f"ANSWER: {model_response['content'][0]['text']}")
    print()
    print(f"Query time: {time.perf_counter() - timer_start:0.4f} seconds")
    print()
    print("The model could access the following source news articles for this answer:")
    for hit in hits:
        print_hit(hit)
    if rejected_hits:
        print()
        print("The following articles were not passed to the model:")
        rejected_hits.sort(key=lambda h: h['_score'], reverse=True)
        for hit in rejected_hits:
            print_hit(hit)
