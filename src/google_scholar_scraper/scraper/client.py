import time

import requests

from google_scholar_scraper.models import Article, ExtractionResult, ExtractionStatus
from google_scholar_scraper.scraper.parser import parse_scholar_articles, parse_scholar_page


BASE_URL = "https://scholar.google.com/scholar"
DEFAULT_TIMEOUT = (5, 15)
DEFAULT_PAGE_DELAY_SECONDS = 1.5
DEFAULT_BACKOFF_SECONDS = 2.0
DEFAULT_MAX_RETRIES = 1
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class ScholarClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: tuple[int, int] = DEFAULT_TIMEOUT,
        page_delay_seconds: float = DEFAULT_PAGE_DELAY_SECONDS,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.session = session or requests.Session()
        if session is None:
            self.session.trust_env = False
        self.session.headers.update(DEFAULT_HEADERS)
        self.timeout = timeout
        self.page_delay_seconds = page_delay_seconds
        self.backoff_seconds = backoff_seconds
        self.max_retries = max_retries


def build_scholar_url(query: str, page: int) -> str:
    return f"https://scholar.google.com/scholar?start={page*10}&q={query}&hl=en&as_sdt=0,5"


def build_scholar_params(query: str, page: int) -> dict[str, str]:
    return {
        "start": str(page * 10),
        "q": query,
        "hl": "en",
        "as_sdt": "0,5",
    }


def fetch_scholar_page(
    query: str,
    page: int,
    session: requests.Session | None = None,
    timeout: tuple[int, int] = DEFAULT_TIMEOUT,
) -> requests.Response:
    active_session = session or requests.Session()
    active_session.headers.update(DEFAULT_HEADERS)
    return active_session.get(BASE_URL, params=build_scholar_params(query, page), timeout=timeout)


def scrape_scholar_articles(query: str, num_pages: int) -> list[Article]:
    result = scrape_scholar(query, num_pages)
    return result.articles


def scrape_scholar(
    query: str,
    num_pages: int,
    client: ScholarClient | None = None,
) -> ExtractionResult:
    active_client = client or ScholarClient()
    articles: list[Article] = []
    successful_pages = 0

    for page in range(num_pages):
        page_number = page + 1
        response_result = _fetch_with_retries(active_client, query, page)
        if isinstance(response_result, ExtractionResult):
            return _with_partial_if_needed(
                response_result,
                articles=articles,
                requested_pages=num_pages,
                successful_pages=successful_pages,
                failure_page=page_number,
            )

        response = response_result
        page_result = parse_scholar_page(response.text, status_code=response.status_code)
        if page_result.status != ExtractionStatus.SUCCESS:
            return _with_partial_if_needed(
                ExtractionResult(
                    status=page_result.status,
                    articles=[],
                    requested_pages=num_pages,
                    successful_pages=successful_pages,
                    failure_page=page_number,
                    message=page_result.message,
                    diagnostic=page_result.diagnostic,
                ),
                articles=articles,
                requested_pages=num_pages,
                successful_pages=successful_pages,
                failure_page=page_number,
            )

        articles.extend(page_result.articles)
        successful_pages += 1

        if page < num_pages - 1 and active_client.page_delay_seconds > 0:
            time.sleep(active_client.page_delay_seconds)

    if not articles:
        return ExtractionResult(
            status=ExtractionStatus.NO_RESULTS,
            articles=[],
            requested_pages=num_pages,
            successful_pages=successful_pages,
            message="Google Scholar returned no results for this query.",
        )

    return ExtractionResult(
        status=ExtractionStatus.SUCCESS,
        articles=articles,
        requested_pages=num_pages,
        successful_pages=successful_pages,
        message=f"Extraction complete. Collected {len(articles)} articles.",
    )


def _fetch_with_retries(
    client: ScholarClient,
    query: str,
    page: int,
) -> requests.Response | ExtractionResult:
    attempts = client.max_retries + 1
    last_error = ""

    for attempt in range(attempts):
        try:
            response = fetch_scholar_page(query, page, session=client.session, timeout=client.timeout)
        except requests.Timeout as exc:
            last_error = exc.__class__.__name__
            if attempt < attempts - 1:
                _backoff(client)
                continue
            return ExtractionResult(
                status=ExtractionStatus.NETWORK_ERROR,
                articles=[],
                requested_pages=0,
                message="Network timeout while contacting Google Scholar.",
                diagnostic=last_error,
            )
        except requests.RequestException as exc:
            last_error = exc.__class__.__name__
            if attempt < attempts - 1 and _is_retryable_request_error(exc):
                _backoff(client)
                continue
            return ExtractionResult(
                status=ExtractionStatus.NETWORK_ERROR,
                articles=[],
                requested_pages=0,
                message="Network error while contacting Google Scholar.",
                diagnostic=last_error,
            )

        if response.status_code == 429:
            return response

        if response.status_code in {502, 503, 504} and attempt < attempts - 1:
            _backoff(client)
            continue

        return response

    return ExtractionResult(
        status=ExtractionStatus.NETWORK_ERROR,
        articles=[],
        requested_pages=0,
        message="Network error while contacting Google Scholar.",
        diagnostic=last_error,
    )


def _backoff(client: ScholarClient) -> None:
    if client.backoff_seconds > 0:
        time.sleep(client.backoff_seconds)


def _is_retryable_request_error(exc: requests.RequestException) -> bool:
    return isinstance(exc, (requests.ConnectionError, requests.Timeout))


def _with_partial_if_needed(
    result: ExtractionResult,
    articles: list[Article],
    requested_pages: int,
    successful_pages: int,
    failure_page: int,
) -> ExtractionResult:
    if articles:
        return ExtractionResult(
            status=ExtractionStatus.PARTIAL_SUCCESS,
            articles=articles,
            requested_pages=requested_pages,
            successful_pages=successful_pages,
            failure_page=failure_page,
            message=(
                f"Extraction stopped early on page {failure_page}: "
                f"{result.message} Exported {len(articles)} collected articles."
            ),
            diagnostic=result.status.value,
        )

    return ExtractionResult(
        status=result.status,
        articles=[],
        requested_pages=requested_pages,
        successful_pages=successful_pages,
        failure_page=failure_page,
        message=result.message,
        diagnostic=result.diagnostic,
    )
