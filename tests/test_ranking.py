import math
import unittest

from google_scholar_scraper.models import Article
from google_scholar_scraper.ranking import (
    article_tokens,
    cosine_similarity,
    rank_articles,
    ranked_articles,
    score_articles,
    tfidf_vector,
    tokenize,
)


class RankingTextPreparationTests(unittest.TestCase):
    def test_tokenize_normalizes_whitespace_case_and_punctuation(self) -> None:
        self.assertEqual(tokenize("  Deep,   LEARNING\tfor\nCancer! "), ["deep", "learning", "for", "cancer"])

    def test_tokenize_preserves_non_latin_text(self) -> None:
        self.assertEqual(tokenize("یادگیری عمیق برای سرطان"), ["یادگیری", "عمیق", "برای", "سرطان"])

    def test_tokenize_handles_empty_text(self) -> None:
        self.assertEqual(tokenize("  \t\n "), [])

    def test_article_tokens_weight_title_more_than_metadata(self) -> None:
        tokens = article_tokens(Article(title="cancer diagnosis", authors="journal cancer"))

        self.assertEqual(tokens.count("cancer"), 4)
        self.assertEqual(tokens.count("diagnosis"), 3)
        self.assertEqual(tokens.count("journal"), 1)


class TfidfAndCosineTests(unittest.TestCase):
    def test_tfidf_vector_handles_one_document(self) -> None:
        vector = tfidf_vector(["cancer", "cancer"], {"cancer": 1.0})

        self.assertEqual(vector, {"cancer": 1.0})

    def test_tfidf_vector_handles_empty_tokens(self) -> None:
        self.assertEqual(tfidf_vector([], {"cancer": 1.0}), {})

    def test_cosine_similarity_identical_vectors(self) -> None:
        self.assertAlmostEqual(cosine_similarity({"a": 1.0}, {"a": 1.0}), 1.0)

    def test_cosine_similarity_unrelated_vectors(self) -> None:
        self.assertEqual(cosine_similarity({"a": 1.0}, {"b": 1.0}), 0.0)

    def test_cosine_similarity_empty_vector(self) -> None:
        self.assertEqual(cosine_similarity({}, {"a": 1.0}), 0.0)


class RelevanceScoringTests(unittest.TestCase):
    def test_matching_title_ranks_above_unrelated_title(self) -> None:
        articles = [
            Article(title="Soil chemistry in arid climates"),
            Article(title="Machine learning for breast cancer diagnosis"),
        ]

        ranked = ranked_articles("machine learning breast cancer diagnosis", articles)

        self.assertEqual(ranked[0].title, "Machine learning for breast cancer diagnosis")
        self.assertGreater(ranked[0].relevance_score, ranked[1].relevance_score)

    def test_scores_are_bounded_and_finite(self) -> None:
        scored = score_articles(
            "machine learning",
            [Article(title="machine learning"), Article(title="unrelated")],
        )

        for article in scored:
            self.assertGreaterEqual(article.relevance_score, 0.0)
            self.assertLessEqual(article.relevance_score, 100.0)
            self.assertFalse(math.isnan(article.relevance_score))
            self.assertFalse(math.isinf(article.relevance_score))

    def test_query_terms_not_seen_in_documents_return_zero_scores(self) -> None:
        scored = score_articles("quantum", [Article(title="machine learning")])

        self.assertEqual(scored[0].relevance_score, 0.0)

    def test_repeated_query_terms_are_deterministic(self) -> None:
        first = score_articles("cancer cancer diagnosis", [Article(title="cancer diagnosis")])
        second = score_articles("cancer cancer diagnosis", [Article(title="cancer diagnosis")])

        self.assertEqual(first[0].relevance_score, second[0].relevance_score)

    def test_single_matching_document_gets_high_score(self) -> None:
        scored = score_articles("machine learning", [Article(title="machine learning")])

        self.assertEqual(scored[0].relevance_score, 100.0)

    def test_equal_scores_preserve_original_order(self) -> None:
        articles = [
            Article(title="Cancer diagnosis"),
            Article(title="Cancer diagnosis"),
        ]

        ranked = rank_articles("cancer", articles)

        self.assertEqual([article.title for article in ranked], ["Cancer diagnosis", "Cancer diagnosis"])

    def test_ranking_disabled_preserves_order_and_scores(self) -> None:
        articles = [
            Article(title="Unrelated"),
            Article(title="Machine learning"),
        ]

        ranked = rank_articles("machine learning", articles, enabled=False)

        self.assertEqual([article.title for article in ranked], ["Unrelated", "Machine learning"])
        self.assertIsNone(ranked[0].relevance_score)


if __name__ == "__main__":
    unittest.main()
