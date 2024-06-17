import sys
import os
from datetime import datetime, timedelta

os.environ['AWS_REGION'] = "eu-west-3"
os.environ['OPENSEARCH_URL'] = 'https://search-osstest2-oss-domain-2fgz4fbh4p2z3ul3z7goiutaay.eu-west-3.es.amazonaws.com'

sys.path.append("query_lambda")

from query_lambda import search, params  # noqa


def test_embedding():
    vector = search.apply_embedding("Hello this is a test")
    assert len(vector) == params.EMBEDDING_MODEL_DIM
    assert isinstance(vector[0], float)


def test_simple_search():
    s = search.Search("UK news")
    hit_list = s.run()
    assert len(hit_list) > 0


def test_date_range_search():
    end_day = datetime.now().date()
    start_day = end_day - timedelta(days=5)
    s = search.DateFilteredSearch("UK news", start_day, end_day)
    hit_list = s.run()
    assert len(hit_list) > 0
