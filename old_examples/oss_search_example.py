"""Search the OSS database interactively."""

import sys
from pathlib import Path
import os
from datetime import datetime, date

sys.path.append(str(Path(__file__).resolve().parent.parent / "query_lambda"))
sys.path.append(
    str(Path(__file__).resolve().parent.parent / "news_scrape_lambda"))

os.environ['OPENSEARCH_URL'] = 'https://search-osstest2-oss-domain-2fgz4fbh4p2z3ul3z7goiutaay.eu-west-3.es.amazonaws.com'
os.environ['AWS_REGION'] = "eu-west-3"

from query_lambda import search  # noqa
from news_scrape_lambda import lambda_function as news_scrape  # noqa


record_id = "c977vyv1yr7o_2024-06-19"

date_range = [datetime.combine(date(2024, 1, 1), datetime.min.time()),
              datetime.combine(date(2025, 1, 1), datetime.min.time())]

##################################################


def get_date_and_time_string(timestamp: float) -> str:
    return str(datetime.fromtimestamp(timestamp).strftime('%d %B %Y %H:%M:%S'))


print()
all_summaries = search.GetAllSummaries(1000).run_summary()
print(f"Found a total of {len(all_summaries)} records in the database.")
all_dates = [x.source.time_read for x in all_summaries]
print(f"Spanning a date range of {get_date_and_time_string(min(all_dates))}"
      f" to {get_date_and_time_string(max(all_dates))}.")


print()
if news_scrape.id_is_in_database(search.os_client, search.OSS_INDEX_NAME,
                                 record_id):
    print(f"Record with id={record_id} IS in the DB.")
else:
    print(f"Record with id={record_id} is NOT in the DB.")


print()
time_summary = search.TimeSearch(date_range[0], date_range[1],
                                 size_per_shard=1000).run_summary()
print(f"Found a total of {len(time_summary)} records in the date range.")
