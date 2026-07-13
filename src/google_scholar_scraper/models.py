from dataclasses import dataclass


@dataclass(frozen=True)
class Article:
    title: str
    authors: str
    link: str

    def to_export_row(self) -> dict[str, str]:
        return {
            "Title": self.title,
            "Authors": self.authors,
            "Link": self.link,
        }
