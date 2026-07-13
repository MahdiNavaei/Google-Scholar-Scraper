from collections import Counter
from collections.abc import Iterable
import math
import re
import unicodedata

from google_scholar_scraper.models import Article


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_TITLE_WEIGHT = 3


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return [token for token in _TOKEN_RE.findall(normalized) if token]


def article_tokens(article: Article) -> list[str]:
    title_tokens = tokenize(article.title)
    author_tokens = tokenize(article.authors)
    return title_tokens * _TITLE_WEIGHT + author_tokens


def score_articles(query: str, articles: Iterable[Article]) -> list[Article]:
    article_list = list(articles)
    query_tokens = tokenize(query)
    document_tokens = [article_tokens(article) for article in article_list]

    if not article_list:
        return []

    scores = _score_tokenized_documents(query_tokens, document_tokens)
    return [
        Article(
            title=article.title,
            authors=article.authors,
            link=article.link,
            relevance_score=score,
        )
        for article, score in zip(article_list, scores)
    ]


def rank_articles(query: str, articles: Iterable[Article], enabled: bool = True) -> list[Article]:
    article_list = list(articles)
    if not enabled:
        return article_list

    scored = score_articles(query, article_list)
    ranked = sorted(enumerate(scored), key=lambda item: (-(item[1].relevance_score or 0.0), item[0]))
    return [article for _, article in ranked]


def ranked_articles(query: str, articles: Iterable[Article], enabled: bool = True) -> list[Article]:
    return rank_articles(query, articles, enabled=enabled)


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}

    counts = Counter(tokens)
    total = sum(counts.values())
    return {token: (count / total) * idf.get(token, 0.0) for token, count in counts.items()}


def cosine_similarity(first: dict[str, float], second: dict[str, float]) -> float:
    if not first or not second:
        return 0.0

    common_tokens = set(first).intersection(second)
    dot_product = sum(first[token] * second[token] for token in common_tokens)
    first_norm = math.sqrt(sum(value * value for value in first.values()))
    second_norm = math.sqrt(sum(value * value for value in second.values()))
    if first_norm == 0.0 or second_norm == 0.0:
        return 0.0

    return dot_product / (first_norm * second_norm)


def _score_tokenized_documents(query_tokens: list[str], document_tokens: list[list[str]]) -> list[float]:
    if not query_tokens:
        return [0.0 for _ in document_tokens]

    corpus = [query_tokens, *document_tokens]
    idf = _idf(corpus)
    query_vector = tfidf_vector(query_tokens, idf)

    scores = []
    for tokens in document_tokens:
        similarity = cosine_similarity(query_vector, tfidf_vector(tokens, idf))
        score = max(0.0, min(100.0, similarity * 100.0))
        scores.append(round(score, 1))

    return scores


def _idf(corpus: list[list[str]]) -> dict[str, float]:
    document_count = len(corpus)
    document_sets = [set(document) for document in corpus]
    vocabulary = set(token for document in document_sets for token in document)
    idf: dict[str, float] = {}
    for token in vocabulary:
        containing_documents = sum(1 for document in document_sets if token in document)
        idf[token] = math.log((document_count + 1) / (containing_documents + 1)) + 1.0
    return idf
