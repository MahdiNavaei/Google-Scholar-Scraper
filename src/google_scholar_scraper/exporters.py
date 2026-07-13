from pathlib import Path
from typing import Iterable
import csv

from openpyxl import Workbook

from google_scholar_scraper.models import Article


EXPORT_COLUMNS = ["Title", "Authors", "Link", "Relevance Score"]


def article_export_rows(articles: Iterable[Article]) -> list[dict[str, object]]:
    return [article.to_export_row() for article in articles]


def save_to_excel(articles: Iterable[Article], filename: str | Path) -> None:
    rows = article_export_rows(articles)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Scholar Articles"
    worksheet.append(EXPORT_COLUMNS)
    for row in rows:
        worksheet.append([row.get(column, "") for column in EXPORT_COLUMNS])
    workbook.save(filename)


def save_to_csv(articles: Iterable[Article], filename: str | Path) -> None:
    rows = article_export_rows(articles)
    with Path(filename).open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
