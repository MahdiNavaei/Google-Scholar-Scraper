from dataclasses import dataclass

from bs4 import BeautifulSoup

from google_scholar_scraper.models import Article, ExtractionStatus


@dataclass(frozen=True)
class PageParseResult:
    status: ExtractionStatus
    articles: list[Article]
    message: str = ""
    diagnostic: str = ""


def parse_scholar_articles(html: str) -> list[Article]:
    return parse_scholar_page(html).articles


def parse_scholar_page(html: str, status_code: int = 200) -> PageParseResult:
    page_status = classify_scholar_page(html, status_code=status_code)
    if page_status != ExtractionStatus.SUCCESS:
        return PageParseResult(
            status=page_status,
            articles=[],
            message=_message_for_status(page_status),
        )

    soup = BeautifulSoup(html, "html.parser")
    results = soup.find_all("div", class_="gs_ri")

    articles = []
    skipped_missing_title = 0
    for result in results:
        title_node = result.find("h3", class_="gs_rt")
        title = title_node.get_text(" ", strip=True) if title_node else ""
        if not title:
            skipped_missing_title += 1
            continue

        authors_node = result.find("div", class_="gs_a")
        authors = authors_node.get_text(" ", strip=True) if authors_node else ""

        link_node = title_node.find("a") if title_node else None
        link = link_node.get("href", "") if link_node else ""
        articles.append(Article(title=title, authors=authors, link=link))

    if not articles:
        return PageParseResult(
            status=ExtractionStatus.PARSING_ERROR,
            articles=[],
            message="Google Scholar returned result containers, but no valid article titles were found.",
            diagnostic=f"skipped_missing_title={skipped_missing_title}",
        )

    diagnostic = ""
    if skipped_missing_title:
        diagnostic = f"skipped_missing_title={skipped_missing_title}"

    return PageParseResult(
        status=ExtractionStatus.SUCCESS,
        articles=articles,
        message="Parsed Google Scholar results.",
        diagnostic=diagnostic,
    )


def classify_scholar_page(html: str, status_code: int = 200) -> ExtractionStatus:
    text = html.lower()

    if status_code == 429 or _has_rate_limit_signal(text):
        return ExtractionStatus.RATE_LIMITED

    if status_code in {401, 403} or _has_blocked_signal(text):
        return ExtractionStatus.BLOCKED

    if status_code < 200 or status_code >= 300:
        return ExtractionStatus.NETWORK_ERROR

    if _has_network_error_signal(text):
        return ExtractionStatus.NETWORK_ERROR

    soup = BeautifulSoup(html, "html.parser")
    results = soup.find_all("div", class_="gs_ri")
    if results:
        return ExtractionStatus.SUCCESS

    if _has_no_results_signal(text):
        return ExtractionStatus.NO_RESULTS

    return ExtractionStatus.PARSING_ERROR


def _has_rate_limit_signal(text: str) -> bool:
    signals = (
        "too many requests",
        "rate limit",
        "temporarily unavailable",
    )
    return any(signal in text for signal in signals)


def _has_blocked_signal(text: str) -> bool:
    signals = (
        "captcha",
        "recaptcha",
        "our systems have detected unusual traffic",
        "unusual traffic from your computer network",
        "not a robot",
        "/sorry/",
        "sorry, but your computer or network may be sending automated queries",
        "before you continue to google",
        "consent.google",
    )
    return any(signal in text for signal in signals)


def _has_network_error_signal(text: str) -> bool:
    signals = (
        "internal server error",
        "the system can't perform the operation now",
        "try again later",
    )
    return any(signal in text for signal in signals)


def _has_no_results_signal(text: str) -> bool:
    signals = (
        "did not match any articles",
        "did not match any results",
        "try different keywords",
        "try fewer keywords",
    )
    return any(signal in text for signal in signals)


def _message_for_status(status: ExtractionStatus) -> str:
    messages = {
        ExtractionStatus.NO_RESULTS: "Google Scholar returned no results for this query.",
        ExtractionStatus.RATE_LIMITED: "Google Scholar rate-limited the request.",
        ExtractionStatus.BLOCKED: "Google Scholar returned a block, consent, or challenge page.",
        ExtractionStatus.NETWORK_ERROR: "Google Scholar returned an unsuccessful HTTP response.",
        ExtractionStatus.PARSING_ERROR: "Google Scholar returned a page that could not be parsed as results.",
        ExtractionStatus.CANCELLED: "Extraction was cancelled.",
    }
    return messages.get(status, "Google Scholar page was classified.")
