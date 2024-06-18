"""Functions for querying the LLM."""

from typing import Any
import json
import logging
import os
from datetime import datetime, date, timedelta

import boto3

from search_models import SearchHit
import params

logger = logging.getLogger()
AWS_REGION = os.environ['AWS_REGION']

llm_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

native_request: dict[str, Any] = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": params.MAX_OUTPUT_TOKENS,
    "messages": [{"role": "user", "content": ""}],
    "temperature": params.TEMPERATURE,
    "top_p": params.TOP_P,
    "top_k": params.TOP_K
}


def invoke_llm(prompt: str) -> str:
    """Send a prompt to the LLM and return the response."""
    native_request['messages'][0]['content'] = prompt
    try:
        response = llm_client.invoke_model(modelId=params.LLM_MODEL_ID,
                                           body=json.dumps(native_request))
    except Exception as e:
        logger.error('Prompt: %s', prompt)
        raise e
    return json.loads(response["body"].read())['content'][0]['text']


def is_question_appropriate(query: str) -> bool:
    """"Identify inappropriate questions (not news related)."""
    today = datetime.now().strftime('%d %B %Y')
    ok_prompt = (f"Today is {today}. Does the following query relate to"
                 " news/occurrences from any time in the last 7 days? Answer"
                 f" yes or no. Do not return any other text. Query: '{query}'")
    ok_response = invoke_llm(ok_prompt)
    return ok_response.lower() == "yes"


def get_relevant_dates(query: str) -> list[date]:
    """Find which dates, if any, are relevant to the query."""
    today = datetime.now().strftime('%d %B %Y')
    date_prompt = (
         f"Today is {today}. Given the following query, what"
         " date or dates are relevant when searching a database"
         " of news articles? Return up to 7 dates, as a Python"
         " list of strings, or return 'null' if no dates are"
         " relevant. Do not return any other text."
         f" Query: '{query}'")

    date_response = invoke_llm(date_prompt)
    date_strings = json.loads(date_response.replace("'", '"'))

    if not date_strings or date_strings == ['null']:
        return []

    try:
        dates = [datetime.strptime(x, "%Y-%m-%d").date() for x in date_strings]
    except Exception:
        logger.error('Could not extract dates from: %s', date_strings)
        return []

    expiry_date = (datetime.now().date()
                   - timedelta(days=params.EXPIRY_PERIOD_DAYS))
    return [x for x in dates if x >= expiry_date]


def create_combined_prompt(query: str, hits: list[SearchHit]) -> str:
    """Combine date, user query, and searched documents into one prompt."""
    today = datetime.now().strftime('%d %B %Y')
    return (f"Today is {today}.\n\n" + "\n\n".join(
        "Summarized BBC news article from"
        f" {datetime.fromtimestamp(x.source.time_read).strftime('%d %B %Y')}."
        f"\n{x.source.chunk}" for x in hits)
        + f"\n\nToday is {today}. {query}")
