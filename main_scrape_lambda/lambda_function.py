"""An AWS Lambda to get URLs from BBC news main page."""

import logging
import os
import json
from typing import Any

import requests
from bs4 import BeautifulSoup
import boto3

LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
ROOT_URL = 'https://www.bbc.co.uk'
URL = 'https://www.bbc.co.uk/news'
SQS_URL = os.getenv('SQS_URL', '')
GET_TIMEOUT_SEC = float(os.getenv('GET_TIMEOUT_SEC', '5'))

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
logger.info('Getting %s with timeout=%s s', URL, GET_TIMEOUT_SEC)

sqs = boto3.client('sqs')


def get_main_page_urls(root_url: str, content: bytes) -> list[str]:
    page = BeautifulSoup(content, 'html.parser')
    links = page.find_all('div',
                          attrs={'data-component': 'mostRead'}
                          )[0].find_all('a')
    return [root_url + link.get('href') for link in links]


def lambda_handler(event: Any, _context_unused: Any) -> None:
    """Define the lambda function."""
    logger.debug('Event: %s', event)

    response = requests.get(URL, timeout=GET_TIMEOUT_SEC)
    if response.status_code != 200:
        logger.error('Get failed; response: %s', response)
        raise ValueError("Bad status code")

    urls = get_main_page_urls(ROOT_URL, response.content)

    logger.debug('Response: %s', ' '.join(urls))

    # Send each url individually
    for url in urls:
        try:
            response = sqs.send_message(QueueUrl=SQS_URL,
                                        MessageBody=json.dumps({'url': url}))
        except Exception:
            logger.error('Send SQS message failed with %s %s', SQS_URL, url)
