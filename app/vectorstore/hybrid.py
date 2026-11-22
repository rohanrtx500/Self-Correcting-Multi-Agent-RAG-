import math
import re
from collections import Counter
from collections.abc import Sequence
from typing import Any

from langchain_core.documents import Document
from loguru import logger


def tokenize(text: str) -> list[str]:
    """Tokenizes text into lowercase alphanumeric tokens."""
    return re.findall(r"\b\w+\b", text.lower())


class SimpleBM25:
    """Lightweight, self-contained Okapi BM25 implementation for lexical keyword search."""

    def __init__(
        self,
        corpus: list[Document],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.doc_len = [len(tokenize(doc.page_content)) for doc in corpus]
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0.0
        self.doc_freqs: list[Counter[str]] = [Counter(tokenize(doc.page_content)) for doc in corpus]
        self.nd: dict[str, int] = Counter()

        for doc_freq in self.doc_freqs:
            for word in doc_freq:
                self.nd[word] += 1

        self.corpus_size = len(corpus)
        self.idf: dict[str, float] = {}
        for word, freq in self.nd.items():
            # Standard Lucene/BM25 IDF with smoothing
            self.idf[word] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

    def get_top_k(self, query: str, k: int = 4) -> list[Document]:
        """Scores all corpus documents against query and returns top-k documents."""
        if not self.corpus or self.corpus_size == 0:
            return []

        query_tokens = tokenize(query)
        scores: list[tuple[float, int]] = []

        for idx, doc_freq in enumerate(self.doc_freqs):
            score = 0.0
            doc_len = self.doc_len[idx]
            for token in query_tokens:
                if token not in doc_freq:
                    continue
                tf = doc_freq[token]
                idf = self.idf.get(token, 0.0)
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avgdl))
                score += idf * (numerator / denominator)
            scores.append((score, idx))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [self.corpus[idx] for score, idx in scores[:k] if score > 0]


def reciprocal_rank_fusion(
    ranked_lists: Sequence[list[Document]],
    k: int = 60,
    top_n: int = 4,
) -> list[Document]:
    """Combines multiple ranked document lists using Reciprocal Rank Fusion (RRF).

    Args:
        ranked_lists: Sequence of document lists from different retrieval methods.
        k: Smoothing constant (standard default is 60).
        top_n: Number of fused documents to return.

    Returns:
        Deduplicated, RRF-scored top_n documents.
    """
    scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    for doc_list in ranked_lists:
        for rank, doc in enumerate(doc_list):
            # Create a unique key per document chunk based on content snippet and source
            doc_key = f"{doc.metadata.get('source', '')}:{doc.page_content[:100]}"
            if doc_key not in doc_map:
                doc_map[doc_key] = doc
            scores[doc_key] = scores.get(doc_key, 0.0) + (1.0 / (k + rank + 1))

    # Sort documents by fused RRF score
    sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [doc_map[key] for key in sorted_keys[:top_n]]


class HybridRetriever:
    """Orchestrates hybrid retrieval combining dense vector search and BM25 keyword search."""

    def __init__(
        self,
        vector_retriever: Any,
        bm25: SimpleBM25 | None = None,
        top_k: int = 4,
    ) -> None:
        self.vector_retriever = vector_retriever
        self.bm25 = bm25
        self.top_k = top_k

    def update_bm25_corpus(self, documents: list[Document]) -> None:
        """Updates the BM25 index with fresh documents."""
        if documents:
            self.bm25 = SimpleBM25(documents)
            logger.debug(f"BM25 index updated with {len(documents)} documents.")

    def invoke(self, query: str) -> list[Document]:
        """Executes hybrid retrieval using dense vectors and BM25 fusion."""
        # 1. Dense vector search
        dense_docs: list[Document] = []
        try:
            if hasattr(self.vector_retriever, "invoke"):
                dense_docs = self.vector_retriever.invoke(query)
            elif callable(self.vector_retriever):
                dense_docs = self.vector_retriever(query)
        except Exception as e:
            logger.warning(f"Dense vector retrieval encountered error: {e}")
            dense_docs = []

        # If BM25 is not initialized or has no corpus, return dense docs
        if not self.bm25 or not self.bm25.corpus:
            return dense_docs[: self.top_k]

        # 2. Sparse BM25 keyword search
        try:
            bm25_docs = self.bm25.get_top_k(query, k=self.top_k)
        except Exception as e:
            logger.warning(f"BM25 retrieval encountered error: {e}")
            bm25_docs = []

        # If only one source succeeded, return it
        if not bm25_docs:
            return dense_docs[: self.top_k]
        if not dense_docs:
            return bm25_docs[: self.top_k]

        # 3. Fuse results with Reciprocal Rank Fusion
        fused = reciprocal_rank_fusion([dense_docs, bm25_docs], top_n=self.top_k)
        logger.debug(
            f"Hybrid search fused {len(dense_docs)} dense + {len(bm25_docs)} BM25 results into {len(fused)} chunks."
        )
        return fused
