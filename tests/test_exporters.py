import tempfile
import unittest
from pathlib import Path

import pandas as pd

from google_scholar_scraper.exporters import save_to_excel
from google_scholar_scraper.models import Article


class ExporterTests(unittest.TestCase):
    def test_export_receives_normalized_article_rows(self) -> None:
        article = Article(title="Deep Learning", authors="A Author", link="https://example.edu/paper")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "articles.xlsx"

            save_to_excel([article], path)

            df = pd.read_excel(path)

        self.assertEqual(list(df.columns), ["Title", "Authors", "Link"])
        self.assertEqual(df.iloc[0]["Title"], "Deep Learning")
        self.assertEqual(df.iloc[0]["Authors"], "A Author")
        self.assertEqual(df.iloc[0]["Link"], "https://example.edu/paper")


if __name__ == "__main__":
    unittest.main()
