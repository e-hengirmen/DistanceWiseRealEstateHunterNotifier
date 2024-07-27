from bs4 import BeautifulSoup
import requests
import cloudscraper
from urllib.parse import urljoin, urlparse

def get_soup(url, cloudflare=False):
    if not cloudflare:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        response = requests.get(url, headers=headers)
        if response.ok:
            return BeautifulSoup(response.text, 'html.parser')
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    response = scraper.get(url)
    if response.ok:
        return BeautifulSoup(response.text, 'html.parser')
    else:
        raise Exception(f'Failed with status code{response.status_code},{url}')

def create_link_from_href(url_with_base, href):
    parsed_url = urlparse(url_with_base)
    base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'

    return urljoin(base_url, href)