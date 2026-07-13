from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
import re
import unicodedata

from google_scholar_scraper.models import Article


_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class DeduplicationResult:
    articles: list[Article]
    duplicates_removed: int = 0
    invalid_removed: int = 0


def normalize_article(article: Article) -> Article:
    return Article(
        title=normalize_display_text(article.title),
        authors=normalize_display_text(article.authors),
        link=normalize_link(article.link),
        relevance_score=article.relevance_score,
    )


def normalize_display_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def normalize_link(value: str) -> str:
    link = value.strip()
    if not link:
        return ""

    parsed = urlsplit(link)
    if not parsed.scheme or not parsed.netloc:
        return link

    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, ""))


def is_valid_article(article: Article) -> bool:
    return bool(normalize_display_text(article.title))


def title_key(article: Article) -> str:
    return _comparison_text_key(article.title)


def canonical_link(article: Article) -> str:
    link = normalize_link(article.link)
    parsed = urlsplit(link)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return link
    return ""


def deduplicate_articles(articles: Iterable[Article]) -> DeduplicationResult:
    deduped: list[Article] = []
    link_to_index: dict[str, int] = {}
    title_to_index: dict[str, int] = {}
    duplicates_removed = 0
    invalid_removed = 0

    for article in articles:
        normalized = normalize_article(article)
        if not is_valid_article(normalized):
            invalid_removed += 1
            continue

        link = canonical_link(normalized)
        title = title_key(normalized)
        existing_index = _find_existing_index(link, title, link_to_index, title_to_index)

        if existing_index is None:
            index = len(deduped)
            deduped.append(normalized)
            if link:
                link_to_index[link] = index
            if title:
                title_to_index[title] = index
            continue

        duplicates_removed += 1
        merged = _merge_articles(deduped[existing_index], normalized)
        deduped[existing_index] = merged

        merged_link = canonical_link(merged)
        merged_title = title_key(merged)
        if merged_link:
            link_to_index[merged_link] = existing_index
        if merged_title:
            title_to_index[merged_title] = existing_index

    return DeduplicationResult(
        articles=deduped,
        duplicates_removed=duplicates_removed,
        invalid_removed=invalid_removed,
    )


def _comparison_text_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    collapsed = normalize_display_text(normalized)
    return collapsed.casefold()


def _find_existing_index(
    link: str,
    title: str,
    link_to_index: dict[str, int],
    title_to_index: dict[str, int],
) -> int | None:
    if link and link in link_to_index:
        return link_to_index[link]
    if title and title in title_to_index:
        return title_to_index[title]
    return None


def _merge_articles(existing: Article, incoming: Article) -> Article:
    return Article(
        title=existing.title or incoming.title,
        authors=existing.authors or incoming.authors,
        link=existing.link or incoming.link,
        relevance_score=existing.relevance_score,
    )
