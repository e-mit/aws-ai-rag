import sys
from pathlib import Path

import news_page_info

sys.path.append("news_scrape")

from news_scrape import lambda_function  # noqa

TEST_URL = 'https://www.bbc.co.uk/news/articles/c99zn92g2qgo'


def test_scrape_news_page():
    with open(Path(__file__).parent / "news_page.txt", "rb") as in_file:
        content = in_file.read()
    id = Path(TEST_URL).stem
    info = lambda_function.scrape_news_page(
        TEST_URL, content, id)
    assert info['time_read'] > news_page_info.info['time_read']
    info['time_read'] = 0
    news_page_info.info['time_read'] = 0
    assert info == news_page_info.info
