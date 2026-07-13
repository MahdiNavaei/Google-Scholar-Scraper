from pathlib import Path
from typing import Iterable

import pandas as pd

from google_scholar_scraper.models import Article


def save_to_excel(articles: Iterable[Article], filename: str | Path) -> None:
    rows = [article.to_export_row() for article in articles]
    df = pd.DataFrame(rows)
    df.to_excel(filename, index=False)
