import unittest
from unittest.mock import patch

from google_scholar_scraper.models import Article, ExtractionResult, ExtractionStatus
from google_scholar_scraper.ui.tkinter_app import MainWindow


class DummyEntry:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


class DummyLabel:
    def __init__(self) -> None:
        self.text = ""

    def config(self, text: str) -> None:
        self.text = text


class UiWiringTests(unittest.TestCase):
    def make_window(self) -> MainWindow:
        window = MainWindow.__new__(MainWindow)
        window.entry_query = DummyEntry("query")
        window.entry_pages = DummyEntry("1")
        window.entry_folder = DummyEntry("")
        window.label_status = DummyLabel()
        return window

    def test_rate_limited_result_does_not_export_empty_excel(self) -> None:
        window = self.make_window()
        result = ExtractionResult(
            status=ExtractionStatus.RATE_LIMITED,
            articles=[],
            requested_pages=1,
            failure_page=1,
            message="Google Scholar rate-limited the request.",
        )

        with patch("google_scholar_scraper.ui.tkinter_app.scrape_scholar", return_value=result), patch(
            "google_scholar_scraper.ui.tkinter_app.save_to_excel"
        ) as save_to_excel:
            window.scrape_articles()

        save_to_excel.assert_not_called()
        self.assertEqual(window.label_status.text, "Google Scholar rate-limited the request.")

    def test_partial_success_exports_collected_articles_with_partial_message(self) -> None:
        window = self.make_window()
        result = ExtractionResult(
            status=ExtractionStatus.PARTIAL_SUCCESS,
            articles=[Article(title="Collected", authors="Author", link="https://example.edu")],
            requested_pages=2,
            successful_pages=1,
            failure_page=2,
            message="Extraction stopped early on page 2: Google Scholar rate-limited the request.",
        )

        with patch("google_scholar_scraper.ui.tkinter_app.scrape_scholar", return_value=result), patch(
            "google_scholar_scraper.ui.tkinter_app.save_to_excel"
        ) as save_to_excel:
            window.scrape_articles()

        save_to_excel.assert_called_once()
        self.assertIn("Extraction stopped early", window.label_status.text)
        self.assertIn("Data saved to scholar_articles.xlsx.", window.label_status.text)


if __name__ == "__main__":
    unittest.main()
