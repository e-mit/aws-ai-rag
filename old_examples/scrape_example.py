import json
import datetime
from pprint import pprint

import requests
from bs4 import BeautifulSoup


GET_TIMEOUT_SEC = 10
#url = 'https://www.bbc.co.uk/news/articles/c844wzmnzjzo'

url = 'https://www.bbc.co.uk/news/articles/clkkdymdwlvo'

response = requests.get(url, timeout=GET_TIMEOUT_SEC)
if response.status_code != 200:
    raise ValueError("Bad status code")

page = BeautifulSoup(response.content, 'html.parser')
json_data = json.loads(page.head.script.text)

title = json_data['headline'].strip()
if title[-1] != '.':
    title += '.'

subtitle = json_data['description'].strip()
if subtitle[-1] != '.':
    subtitle += '.'

info = {
    'title': title,
    'subtitle': subtitle,
    'url': url,
    'last_modified': json_data['dateModified'],
    'date_read': datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
    'related': [x.text.strip() for x in page.find_all(
        "a", {"class": "ssrcss-z69h1q-StyledLink ed0g1kj0"})],
    'paragraph_1': page.b.text.strip(),
    'paragraphs_2_3': (page.p.next_sibling.text.strip() + ' '
                       + page.p.next_sibling.next_sibling.text.strip())
    }


x = page.find_all("div", {"class": "ssrcss-7uxr49-RichTextContainer e5tfeyi1"})
full_text = " ".join(" ".join(z.text.strip() for z in y.find_all(
    "p", {"class": "ssrcss-1q0x1qg-Paragraph e1jhz7w10"})
    if z.contents and z.contents[0].name in [None, 'b']) for y in x)

pprint(info)
