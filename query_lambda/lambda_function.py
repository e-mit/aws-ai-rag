"""An AWS Lambda to query an LLM using RAG."""

import logging
import os
from typing import Any

import params
import query
from search import Search, DateFilteredSearch
from search_models import SearchHit

LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
AWS_REGION = os.environ['AWS_REGION']

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
logger.debug('Starting')


def lambda_handler(event: Any, _context_unused: Any) -> dict[str, Any]:
    """Define the lambda function."""
    logger.debug('Event: %s', event)

    if not query.is_question_appropriate(event['query']):
        return {'answer': params.INAPPROPRIATE_REPLY, 'article_refs': []}

    dates = query.get_relevant_dates(event['query'])

    if dates is None:
        hits = Search(event['query']).run()
    else:
        # Do a separate search for each day, and keep only the best results.
        all_hits: list[SearchHit] = []
        for day in dates:
            all_hits.extend(DateFilteredSearch(event['query'], day, day).run())
        all_hits.sort(key=lambda h: h.score, reverse=True)
        n_to_keep = min([params.QUERY_SIZE * len(dates), params.HIT_LIMIT])
        hits = all_hits[0:n_to_keep]

    # Reject low scoring hits
    hits = [x for x in hits if x.score >= params.SCORE_THRESHOLD]
    if not hits:
        return {'answer': params.NO_RESULTS_REPLY, 'article_refs': []}

    combined_prompt = query.create_combined_prompt(event['query'], hits)
    model_response = query.invoke_llm(combined_prompt)
    return {'answer': model_response,
            'article_refs': [x.get_article_summary() for x in hits]}
