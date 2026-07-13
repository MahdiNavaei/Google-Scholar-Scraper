import unittest
from pathlib import Path

from google_scholar_scraper.models import ExtractionStatus
from google_scholar_scraper.scraper.parser import classify_scholar_page, parse_scholar_page


FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class ParserTests(unittest.TestCase):
    def test_successful_multiple_result_parsing(self) -> None:
        result = parse_scholar_page(fixture("scholar_results_basic.html"))

        self.assertEqual(result.status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(result.articles), 2)
        self.assertEqual(result.articles[0].title, "Example Paper One")
        self.assertEqual(result.articles[0].authors, "A Author - Journal, 2024")
        self.assertEqual(result.articles[0].link, "https://example.edu/paper-one")

    def test_missing_optional_metadata_and_link_do_not_crash(self) -> None:
        result = parse_scholar_page(fixture("scholar_results_missing_optional.html"))

        self.assertEqual(result.status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(result.articles), 1)
        self.assertEqual(result.articles[0].title, "Citation only result without external link")
        self.assertEqual(result.articles[0].authors, "")
        self.assertEqual(result.articles[0].link, "")

    def test_genuine_no_results_detection(self) -> None:
        result = parse_scholar_page(fixture("scholar_results_empty.html"))

        self.assertEqual(result.status, ExtractionStatus.NO_RESULTS)
        self.assertEqual(result.articles, [])

    def test_rate_limit_text_detection(self) -> None:
        result = parse_scholar_page(fixture("scholar_rate_limited.html"))

        self.assertEqual(result.status, ExtractionStatus.RATE_LIMITED)

    def test_http_429_detection(self) -> None:
        status = classify_scholar_page("<html><body>anything</body></html>", status_code=429)

        self.assertEqual(status, ExtractionStatus.RATE_LIMITED)

    def test_blocked_challenge_detection(self) -> None:
        result = parse_scholar_page(fixture("scholar_blocked.html"))

        self.assertEqual(result.status, ExtractionStatus.BLOCKED)

    def test_incompatible_page_is_parsing_error(self) -> None:
        result = parse_scholar_page(fixture("scholar_incompatible.html"))

        self.assertEqual(result.status, ExtractionStatus.PARSING_ERROR)


if __name__ == "__main__":
    unittest.main()
