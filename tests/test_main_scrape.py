import sys
from pathlib import Path

import main_page_list

sys.path.append("main_scrape_lambda")

from main_scrape_lambda import lambda_function  # noqa


def test_get_main_page_urls():
    with open(Path(__file__).parent / "main_page.txt", "rb") as in_file:
        content = in_file.read()
    url_list_test = lambda_function.get_main_page_urls(
        lambda_function.ROOT_URL, content)
    assert set(url_list_test) == set(main_page_list.links)
