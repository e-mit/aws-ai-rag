import sys
from pathlib import Path
from datetime import datetime

from . import news_page_info

sys.path.append("news_scrape_lambda")

from news_scrape_lambda import lambda_function  # noqa

TEST_URL = 'https://www.bbc.co.uk/news/articles/c99zn92g2qgo'


def test_scrape_news_page():
    with open(Path(__file__).parent / "news_page.txt", "rb") as in_file:
        content = in_file.read()
    id = Path(TEST_URL).stem
    info = lambda_function.scrape_news_page(
        TEST_URL, content, id, datetime.now())
    assert info['time_read'] > news_page_info.info['time_read']
    info['date'] = 0
    info['time_read'] = 0
    news_page_info.info['time_read'] = 0
    news_page_info.info['date'] = 0
    for k in info:
        assert info[k] == news_page_info.info[k]
