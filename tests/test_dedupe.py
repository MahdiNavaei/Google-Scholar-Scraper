import unittest

from google_scholar_scraper.dedupe import (
    canonical_link,
    deduplicate_articles,
    is_valid_article,
    normalize_article,
    normalize_display_text,
    normalize_link,
    title_key,
)
from google_scholar_scraper.models import Article


class NormalizationTests(unittest.TestCase):
    def test_display_text_collapses_whitespace_without_changing_punctuation_or_unicode(self) -> None:
        text = "  یادگیری\t عمیق\nبرای   پزشکی: α + β!  "

        self.assertEqual(normalize_display_text(text), "یادگیری عمیق برای پزشکی: α + β!")

    def test_article_normalization_preserves_readable_case(self) -> None:
        article = normalize_article(Article(title="  Deep   Learning  ", authors="\nA\tAuthor  ", link=" https://Example.edu/paper#part "))

        self.assertEqual(article.title, "Deep Learning")
        self.assertEqual(article.authors, "A Author")
        self.assertEqual(article.link, "https://example.edu/paper")

    def test_title_key_is_case_insensitive_and_whitespace_insensitive(self) -> None:
        first = title_key(Article(title="  Deep   Learning for Medical Imaging  "))
        second = title_key(Article(title="DEEP LEARNING FOR MEDICAL IMAGING"))

        self.assertEqual(first, second)

    def test_link_normalization_preserves_empty_and_relative_values(self) -> None:
        self.assertEqual(normalize_link("   "), "")
        self.assertEqual(normalize_link(" /scholar?cluster=1#frag "), "/scholar?cluster=1#frag")

    def test_canonical_link_requires_http_url(self) -> None:
        self.assertEqual(canonical_link(Article(title="Title", link="https://Example.edu/a#b")), "https://example.edu/a")
        self.assertEqual(canonical_link(Article(title="Title", link="/scholar?cluster=1")), "")


class ValidationTests(unittest.TestCase):
    def test_normal_article_is_valid(self) -> None:
        self.assertTrue(is_valid_article(Article(title="Valid title", authors="Author", link="")))

    def test_missing_link_remains_valid(self) -> None:
        self.assertTrue(is_valid_article(Article(title="Citation only result", authors="", link="")))

    def test_missing_authors_remains_valid(self) -> None:
        self.assertTrue(is_valid_article(Article(title="Title", authors="", link="https://example.edu")))

    def test_empty_title_is_invalid(self) -> None:
        self.assertFalse(is_valid_article(Article(title=" \n\t ", authors="Author", link="https://example.edu")))


class DeduplicationTests(unittest.TestCase):
    def test_exact_duplicate_is_removed(self) -> None:
        result = deduplicate_articles(
            [
                Article(title="Title", authors="Author", link="https://example.edu/a"),
                Article(title="Title", authors="Author", link="https://example.edu/a"),
            ]
        )

        self.assertEqual(len(result.articles), 1)
        self.assertEqual(result.duplicates_removed, 1)

    def test_duplicate_title_with_whitespace_and_capitalization_is_removed(self) -> None:
        result = deduplicate_articles(
            [
                Article(title="  Deep   Learning for Medical Imaging  ", authors="A", link=""),
                Article(title="DEEP LEARNING FOR MEDICAL IMAGING", authors="A", link=""),
            ]
        )

        self.assertEqual(len(result.articles), 1)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual(result.articles[0].title, "Deep Learning for Medical Imaging")

    def test_same_canonical_link_is_duplicate(self) -> None:
        result = deduplicate_articles(
            [
                Article(title="First title", authors="A", link="https://example.edu/paper#section"),
                Article(title="Second title", authors="B", link="https://EXAMPLE.edu/paper"),
            ]
        )

        self.assertEqual(len(result.articles), 1)
        self.assertEqual(result.articles[0].title, "First title")

    def test_same_title_merges_missing_link_from_later_record(self) -> None:
        result = deduplicate_articles(
            [
                Article(title="Shared title", authors="Author", link=""),
                Article(title=" shared   title ", authors="", link="https://example.edu/shared"),
            ]
        )

        self.assertEqual(len(result.articles), 1)
        self.assertEqual(result.articles[0].link, "https://example.edu/shared")
        self.assertEqual(result.articles[0].authors, "Author")

    def test_different_titles_remain_distinct(self) -> None:
        result = deduplicate_articles(
            [
                Article(title="Deep Learning for Medical Imaging", authors="", link=""),
                Article(title="Deep Learning for Medical Image Segmentation", authors="", link=""),
            ]
        )

        self.assertEqual(len(result.articles), 2)
        self.assertEqual(result.duplicates_removed, 0)

    def test_stable_first_seen_ordering(self) -> None:
        result = deduplicate_articles(
            [
                Article(title="First", authors="", link=""),
                Article(title="Second", authors="", link=""),
                Article(title="first", authors="", link="https://example.edu/first"),
                Article(title="Third", authors="", link=""),
            ]
        )

        self.assertEqual([article.title for article in result.articles], ["First", "Second", "Third"])
        self.assertEqual(result.articles[0].link, "https://example.edu/first")

    def test_invalid_empty_title_is_removed(self) -> None:
        result = deduplicate_articles([Article(title="  ", authors="Author", link="https://example.edu")])

        self.assertEqual(result.articles, [])
        self.assertEqual(result.invalid_removed, 1)


if __name__ == "__main__":
    unittest.main()
