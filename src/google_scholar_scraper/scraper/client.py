import requests

from google_scholar_scraper.scraper.parser import parse_scholar_articles
from google_scholar_scraper.models import Article


def build_scholar_url(query: str, page: int) -> str:
    return f"https://scholar.google.com/scholar?start={page*10}&q={query}&hl=en&as_sdt=0,5"


def fetch_scholar_page(query: str, page: int) -> str:
    url = build_scholar_url(query, page)
    response = requests.get(url)
    return response.text


def scrape_scholar_articles(query: str, num_pages: int) -> list[Article]:
    articles = []
    page = 0
    while page < num_pages:
        html = fetch_scholar_page(query, page)
        articles.extend(parse_scholar_articles(html))
        page += 1

    return articles
