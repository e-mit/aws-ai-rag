"""Get the 10 'most read' link URLs from the BBC news homepage."""
import requests
from bs4 import BeautifulSoup


GET_TIMEOUT_SEC = 10
root_url = 'https://www.bbc.co.uk'
url = 'https://www.bbc.co.uk/news'

response = requests.get(url, timeout=GET_TIMEOUT_SEC)
if response.status_code != 200:
    raise ValueError("Bad status code")

page = BeautifulSoup(response.content, 'html.parser')

links = page.find_all('div', attrs={'data-component': 'mostRead'}
                      )[0].find_all('a')
urls = [root_url + link.get('href') for link in links]
