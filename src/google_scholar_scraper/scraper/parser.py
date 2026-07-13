from bs4 import BeautifulSoup

from google_scholar_scraper.models import Article


def parse_scholar_articles(html: str) -> list[Article]:
    soup = BeautifulSoup(html, "html.parser")
    results = soup.find_all("div", class_="gs_ri")

    articles = []
    for result in results:
        title = result.find("h3", class_="gs_rt").text
        authors = result.find("div", class_="gs_a").text
        link = result.find("a")["href"]
        articles.append(Article(title=title, authors=authors, link=link))

    return articles
