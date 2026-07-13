from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Article:
    title: str
    authors: str = ""
    link: str = ""

    def to_export_row(self) -> dict[str, str]:
        return {
            "Title": self.title,
            "Authors": self.authors,
            "Link": self.link,
        }


class ExtractionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    RATE_LIMITED = "RATE_LIMITED"
    BLOCKED = "BLOCKED"
    NETWORK_ERROR = "NETWORK_ERROR"
    PARSING_ERROR = "PARSING_ERROR"


@dataclass(frozen=True)
class ExtractionResult:
    status: ExtractionStatus
    articles: list[Article]
    requested_pages: int
    successful_pages: int = 0
    failure_page: int | None = None
    message: str = ""
    diagnostic: str = ""
    duplicates_removed: int = 0
    invalid_articles_removed: int = 0

    @property
    def has_articles(self) -> bool:
        return bool(self.articles)
