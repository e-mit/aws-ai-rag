"""An AWS Lambda to scrape information from a BBC news page."""

import logging
import os
from typing import Any
import json
import datetime
import pathlib

import requests
from bs4 import BeautifulSoup
from opensearchpy import OpenSearch, RequestsHttpConnection
import boto3
from requests_aws4auth import AWS4Auth  # type: ignore

from . import sqs_event

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'DEBUG'))

GET_TIMEOUT_SEC = float(os.getenv('GET_TIMEOUT_SEC', '5'))
OPENSEARCH_URL = os.getenv('OPENSEARCH_URL', "https://example.com")
if OPENSEARCH_URL[0:4] != 'http':
    OPENSEARCH_URL = 'https://' + OPENSEARCH_URL
AWS_REGION = os.getenv('AWS_REGION', "eu-west-3")
EMBEDDING_MODEL_ID = "amazon.titan-embed-image-v1"
EMBEDDING_DIMENSION = 1024
INDEX_NAME = "news"
SERVICE = 'es'

embedding_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
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


def id_is_in_database(client: OpenSearch, index: str, _id: str) -> bool:
    """Find out if the id is already in the database."""
    query_match = {
        "size": 2,  # Limits number of hits returned
        "query": {"ids": {"values": [_id]}}
    }
    results = client.search(
        body=query_match,
        index=index,
        _source="false",  # type: ignore
    )
    nhits = len(results["hits"]["hits"])
    if nhits > 1:
        raise KeyError(f"Duplicate ID in database: {_id}")
    return nhits != 0


def apply_embedding(embed_client, embed_model: str,
                    input_text: str) -> list[float]:
    """Convert input text to a vector embedding."""
    response = embed_client.invoke_model(
        modelId=embed_model, body=json.dumps({"inputText": input_text}))
    return json.loads(response["body"].read())["embedding"]


def scrape_news_page(url: str, content: bytes, _id: str,
                     time_now: datetime.datetime) -> dict['str', Any]:
    """Extract the useful data from the news page."""
    page = BeautifulSoup(content, 'html.parser')
    if page.head is None or page.head.script is None:
        raise ValueError("Head format is incorrect.")
    json_data = json.loads(page.head.script.text)

    title = json_data['headline'].strip()
    if title[-1] != '.':
        title += '.'

    subtitle = json_data['description'].strip()
    if subtitle[-1] != '.':
        subtitle += '.'

    paragraphs_1_2_3 = []
    try:
        for div in page.find_all(
                'div', {'class': 'ssrcss-7uxr49-RichTextContainer e5tfeyi1'}):
            for p in div.find_all(
                    'p', {'class': 'ssrcss-1q0x1qg-Paragraph e1jhz7w10'}):
                if p.contents and p.contents[0].name in [None, 'b']:
                    paragraphs_1_2_3.append(p.text.strip())
                    if len(paragraphs_1_2_3) == 3:
                        raise StopIteration("Break loop")
    except StopIteration:  # nosec
        pass

    info = {
        'id': _id,
        'title': title,
        'subtitle': subtitle,
        'url': url,
        'date': str(time_now.date()),
        'last_modified': datetime.datetime.fromisoformat(
                json_data['dateModified'].replace('Z', '+00:00')
                ).timestamp(),
        'time_read': time_now.timestamp(),
        'related': [x.text.strip() for x in page.find_all(
            "a", {"class": "ssrcss-z69h1q-StyledLink ed0g1kj0"})],
        'paragraph_1': paragraphs_1_2_3[0],
        'paragraphs_2_3': (paragraphs_1_2_3[1] + ' '
                           + paragraphs_1_2_3[2])
        }
    keys = ['title', 'subtitle', 'paragraph_1', 'paragraphs_2_3']
    info['chunk'] = (" ".join(info[k] for k in keys) + " "
                     + ". ".join(j for j in info['related']) + ".")
    info['embedding'] = apply_embedding(embedding_client,
                                        EMBEDDING_MODEL_ID,
                                        info['chunk'])

    x = page.find_all(
        "div", {"class": "ssrcss-7uxr49-RichTextContainer e5tfeyi1"})
    info['full_text'] = " ".join(" ".join(z.text.strip() for z in y.find_all(
        "p", {"class": "ssrcss-1q0x1qg-Paragraph e1jhz7w10"})
        if z.contents and z.contents[0].name in [None, 'b']
        ) for y in x)
    return info


def lambda_handler(event: dict[str, Any], _context_unused: Any) -> None:
    """Define the lambda function."""
    logger.debug('Event: %s', event)

    for url_dict in sqs_event.extract(event):
        logger.debug("Extracted url: %s", url_dict['url'])

        time_now = datetime.datetime.now()
        _id = f"{pathlib.Path(url_dict['url']).stem}_{time_now.date()}"

        response = requests.get(url_dict['url'], timeout=GET_TIMEOUT_SEC)
        if response.status_code != 200:
            raise ValueError("Bad status code")

        info = scrape_news_page(url_dict['url'], response.content,
                                _id, time_now)
        oss_client.index(
            index=INDEX_NAME,
            body=info,
            id=_id,
            refresh=True  # type: ignore
        )
