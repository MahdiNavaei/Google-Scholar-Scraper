import unittest
from unittest.mock import patch

import requests

from google_scholar_scraper.models import ExtractionStatus
from google_scholar_scraper.scraper.client import (
    ScholarClient,
    build_scholar_params,
    scrape_scholar,
)


BASIC_HTML = """
<html><body>
  <div class="gs_ri">
    <h3 class="gs_rt"><a href="https://example.edu/one">One</a></h3>
    <div class="gs_a">Author One</div>
  </div>
</body></html>
"""

DUPLICATE_HTML = """
<html><body>
  <div class="gs_ri">
    <h3 class="gs_rt"><a href="https://example.edu/duplicate#section">  Shared
      Title  </a></h3>
    <div class="gs_a"> Author   One </div>
  </div>
  <div class="gs_ri">
    <h3 class="gs_rt"><a href="https://example.edu/unique">Unique Title</a></h3>
    <div class="gs_a">Author Two</div>
  </div>
</body></html>
"""

DUPLICATE_SECOND_PAGE_HTML = """
<html><body>
  <div class="gs_ri">
    <h3 class="gs_rt"><a href="https://example.edu/duplicate">SHARED TITLE</a></h3>
    <div class="gs_a">Author One</div>
  </div>
</body></html>
"""

RATE_LIMIT_HTML = "<html><body><h1>Too many requests</h1></body></html>"
BLOCKED_HTML = "<html><body>Our systems have detected unusual traffic. CAPTCHA</body></html>"
EMPTY_HTML = "<html><body>Your search did not match any articles.</body></html>"


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code


class FakeSession:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = responses
        self.headers = {}
        self.calls = []

    def get(self, url: str, params: dict[str, str], timeout: tuple[int, int]) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class ClientTests(unittest.TestCase):
    def test_build_scholar_params_preserves_pagination_meaning(self) -> None:
        params = build_scholar_params("machine learning", 2)

        self.assertEqual(params["q"], "machine learning")
        self.assertEqual(params["start"], "20")
        self.assertEqual(params["hl"], "en")
        self.assertEqual(params["as_sdt"], "0,5")

    def test_successful_multi_page_extraction(self) -> None:
        session = FakeSession([FakeResponse(BASIC_HTML), FakeResponse(BASIC_HTML)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0)

        result = scrape_scholar("query", 2, client=client)

        self.assertEqual(result.status, ExtractionStatus.SUCCESS)
        self.assertEqual(result.successful_pages, 2)
        self.assertEqual(len(result.articles), 1)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual(len(session.calls), 2)

    def test_successful_multi_page_extraction_removes_duplicates(self) -> None:
        session = FakeSession([FakeResponse(DUPLICATE_HTML), FakeResponse(DUPLICATE_SECOND_PAGE_HTML)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0)

        result = scrape_scholar("query", 2, client=client)

        self.assertEqual(result.status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(result.articles), 2)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual([article.title for article in result.articles], ["Shared Title", "Unique Title"])
        self.assertEqual(result.articles[0].link, "https://example.edu/duplicate")
        self.assertIn("Removed 1 duplicate articles.", result.message)
        self.assertIsNotNone(result.articles[0].relevance_score)

    def test_ranking_disabled_preserves_deduplicated_scholar_order(self) -> None:
        session = FakeSession([FakeResponse(DUPLICATE_HTML), FakeResponse(DUPLICATE_SECOND_PAGE_HTML)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0)

        result = scrape_scholar("shared title", 2, client=client, ranking_enabled=False)

        self.assertEqual(result.status, ExtractionStatus.SUCCESS)
        self.assertEqual([article.title for article in result.articles], ["Shared Title", "Unique Title"])
        self.assertIsNone(result.articles[0].relevance_score)

    def test_later_page_rate_limit_preserves_partial_results(self) -> None:
        session = FakeSession([FakeResponse(BASIC_HTML), FakeResponse(RATE_LIMIT_HTML, 429)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0)

        result = scrape_scholar("query", 2, client=client)

        self.assertEqual(result.status, ExtractionStatus.PARTIAL_SUCCESS)
        self.assertEqual(result.successful_pages, 1)
        self.assertEqual(result.failure_page, 2)
        self.assertEqual(len(result.articles), 1)
        self.assertEqual(result.diagnostic, ExtractionStatus.RATE_LIMITED.value)

    def test_partial_success_removes_duplicates_from_successful_pages(self) -> None:
        session = FakeSession(
            [
                FakeResponse(DUPLICATE_HTML),
                FakeResponse(DUPLICATE_SECOND_PAGE_HTML),
                FakeResponse(RATE_LIMIT_HTML, 429),
            ]
        )
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0)

        result = scrape_scholar("query", 3, client=client)

        self.assertEqual(result.status, ExtractionStatus.PARTIAL_SUCCESS)
        self.assertEqual(result.successful_pages, 2)
        self.assertEqual(result.failure_page, 3)
        self.assertEqual(len(result.articles), 2)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual(result.diagnostic, ExtractionStatus.RATE_LIMITED.value)
        self.assertIsNotNone(result.articles[0].relevance_score)

    def test_rate_limited_first_page_is_not_success(self) -> None:
        session = FakeSession([FakeResponse(RATE_LIMIT_HTML, 429)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0)

        result = scrape_scholar("query", 1, client=client)

        self.assertEqual(result.status, ExtractionStatus.RATE_LIMITED)
        self.assertFalse(result.articles)

    def test_blocked_page_is_not_no_results(self) -> None:
        session = FakeSession([FakeResponse(BLOCKED_HTML)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0)

        result = scrape_scholar("query", 1, client=client)

        self.assertEqual(result.status, ExtractionStatus.BLOCKED)

    def test_no_results_page_is_explicit(self) -> None:
        session = FakeSession([FakeResponse(EMPTY_HTML)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0)

        result = scrape_scholar("query", 1, client=client)

        self.assertEqual(result.status, ExtractionStatus.NO_RESULTS)

    def test_zero_score_articles_are_preserved(self) -> None:
        session = FakeSession([FakeResponse(BASIC_HTML)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0)

        result = scrape_scholar("quantum", 1, client=client)

        self.assertEqual(result.status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(result.articles), 1)
        self.assertEqual(result.articles[0].relevance_score, 0.0)

    def test_network_timeout_is_network_error_after_bounded_retry(self) -> None:
        session = FakeSession([requests.Timeout("first"), requests.Timeout("second")])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0, max_retries=1)

        result = scrape_scholar("query", 1, client=client)

        self.assertEqual(result.status, ExtractionStatus.NETWORK_ERROR)
        self.assertEqual(len(session.calls), 2)

    def test_connection_error_can_retry_successfully(self) -> None:
        session = FakeSession([requests.ConnectionError("temporary"), FakeResponse(BASIC_HTML)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0, max_retries=1)

        result = scrape_scholar("query", 1, client=client)

        self.assertEqual(result.status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(session.calls), 2)

    def test_temporary_http_error_can_retry_successfully(self) -> None:
        session = FakeSession([FakeResponse("temporary outage", 503), FakeResponse(BASIC_HTML)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0, max_retries=1)

        result = scrape_scholar("query", 1, client=client)

        self.assertEqual(result.status, ExtractionStatus.SUCCESS)
        self.assertEqual(len(session.calls), 2)

    def test_parser_error_after_success_preserves_partial_results(self) -> None:
        incompatible = "<html><body><div id='gs_res_ccl_mid'>changed structure</div></body></html>"
        session = FakeSession([FakeResponse(BASIC_HTML), FakeResponse(incompatible)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0)

        result = scrape_scholar("query", 2, client=client)

        self.assertEqual(result.status, ExtractionStatus.PARTIAL_SUCCESS)
        self.assertEqual(result.diagnostic, ExtractionStatus.PARSING_ERROR.value)
        self.assertEqual(len(result.articles), 1)

    def test_no_retry_for_rate_limit(self) -> None:
        session = FakeSession([FakeResponse(RATE_LIMIT_HTML, 429), FakeResponse(BASIC_HTML)])
        client = ScholarClient(session=session, page_delay_seconds=0, backoff_seconds=0, max_retries=1)

        result = scrape_scholar("query", 1, client=client)

        self.assertEqual(result.status, ExtractionStatus.RATE_LIMITED)
        self.assertEqual(len(session.calls), 1)

    def test_request_pacing_between_successful_pages(self) -> None:
        session = FakeSession([FakeResponse(BASIC_HTML), FakeResponse(BASIC_HTML)])
        client = ScholarClient(session=session, page_delay_seconds=1.5, backoff_seconds=0)

        with patch("google_scholar_scraper.scraper.client.time.sleep") as sleep:
            scrape_scholar("query", 2, client=client)

        sleep.assert_called_once_with(1.5)


if __name__ == "__main__":
    unittest.main()
