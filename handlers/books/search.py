"""
IDF-weighted search functionality for BooksHandler.

Extracts search-related logic into a reusable mixin class.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, TYPE_CHECKING

from lib.sheet_utils import tokenize

if TYPE_CHECKING:
    from handlers.books.handler import BooksHandler


def _calculate_idf(term: str, doc_freq: dict[str, int], total_docs: int) -> float:
    """
    Calculate BM25-style IDF for a term.

    Args:
        term: The search term
        doc_freq: Document frequency dict (term -> count)
        total_docs: Total number of documents

    Returns:
        IDF score for the term
    """
    df = doc_freq.get(term, 0)
    return math.log(((total_docs - df + 0.5) / (df + 0.5)) + 1)


class SearchMixin:
    """
    IDF-weighted search functionality for BooksHandler.

    This mixin provides methods for scoring and ranking book candidates
    based on IDF-weighted search algorithms.
    """

    # Subject detection keywords (defined in handler, referenced here)
    SUBJECT_KEYS: list[str]

    def _score_candidates(self: "BooksHandler", query: str) -> list[dict[str, Any]]:
        """Score all parent rows against the query."""
        from lib.common import normalize

        q_normalized = normalize(query)
        q_tokens = tokenize(query)
        query_subject = self._detect_subject(q_tokens)

        # Build document frequency and collect parent rows
        doc_freq, parent_rows = self._build_doc_freq()
        total_docs = len(parent_rows) or 1

        # Calculate IDF for query tokens
        unique_q_tokens = list(set(q_tokens))
        sum_idf_q = sum(_calculate_idf(t, doc_freq, total_docs) for t in unique_q_tokens) or 1

        candidates = []
        for r in parent_rows:
            score, reason = self._score_single(
                r, q_normalized, unique_q_tokens, doc_freq, total_docs, sum_idf_q, query_subject
            )
            if score > 0:
                candidates.append({
                    "book_id": r["id"],
                    "title": r["title"],
                    "subject": r["subject"],
                    "score": round(score, 4),
                    "reason": reason,
                })

        candidates.sort(key=lambda x: -x["score"])
        return candidates

    def _build_doc_freq(self: "BooksHandler") -> tuple[dict[str, int], list[dict[str, Any]]]:
        """Build document frequency map and parent row list."""
        seen: set[str] = set()
        doc_freq: dict[str, int] = defaultdict(int)
        parent_rows: list[dict[str, Any]] = []

        for row in self.values[1:]:
            id_raw = str(self.get_cell(row, "id")).strip()
            title_raw = str(self.get_cell(row, "title")).strip()
            subject_raw = str(self.get_cell(row, "subject")).strip()

            if not id_raw and not title_raw and not subject_raw:
                continue
            if not id_raw:  # Child row (chapter)
                continue
            if id_raw in seen:
                continue
            seen.add(id_raw)

            parent_rows.append({
                "id": id_raw,
                "title": title_raw,
                "subject": subject_raw,
            })

            # Count document frequency
            tok_set = set(tokenize(title_raw))
            for t in tok_set:
                doc_freq[t] += 1

        return doc_freq, parent_rows

    def _detect_subject(self: "BooksHandler", tokens: list[str]) -> str | None:
        """Detect subject keyword from query tokens."""
        return next(
            (k for k in self.SUBJECT_KEYS if k.lower() in [t.lower() for t in tokens]),
            None
        )

    def _score_single(
        self: "BooksHandler",
        r: dict[str, Any],
        q_normalized: str,
        unique_q_tokens: list[str],
        doc_freq: dict[str, int],
        total_docs: int,
        sum_idf_q: float,
        query_subject: str | None,
    ) -> tuple[float, str]:
        """Score a single candidate against the query."""
        from lib.common import normalize

        hay = [normalize(r["id"]), normalize(r["title"]), normalize(r["subject"])]
        hay = [h for h in hay if h and len(h) >= 2]

        combined_norm = normalize(r["title"])
        title_tok_set = set(tokenize(r["title"]))

        # Calculate IDF coverage
        idf_hit_fwd = sum(_calculate_idf(t, doc_freq, total_docs)
                         for t in unique_q_tokens if t in title_tok_set)
        cov_idf_fwd = idf_hit_fwd / sum_idf_q

        # Base scoring
        score = 0.0
        reason = ""

        if any(h == q_normalized for h in hay):
            score = 1.0
            reason = "exact"
        elif q_normalized in combined_norm:
            score = 0.95
            reason = "phrase"
        elif any(q_normalized in h for h in hay):
            score = 0.90
            reason = "partial_target"
        elif cov_idf_fwd > 0:
            score = 0.80
            reason = "coverage_q_in_title"
        else:
            short = q_normalized[:3] if len(q_normalized) >= 3 else ""
            if short and any(short in h for h in hay):
                score = 0.72
                reason = "fuzzy3"

        # Bonus
        bonus = 0.0
        if cov_idf_fwd > 0:
            bonus += min(0.12, 0.12 * cov_idf_fwd)
        if combined_norm.startswith(q_normalized):
            bonus += 0.02
        if query_subject and normalize(query_subject) == normalize(r["subject"]):
            bonus += 0.02

        return min(1, score + bonus), reason

    def _apply_gap_cutoff(self: "BooksHandler", candidates: list[dict], limit: int) -> list[dict]:
        """Apply score gap cutoff and limit."""
        min_gap = 0.05
        cut_index = len(candidates)
        for i in range(len(candidates) - 1):
            if candidates[i]["score"] - candidates[i + 1]["score"] >= min_gap:
                cut_index = i + 1
                break

        return candidates[:min(limit, cut_index)]

    def _calculate_confidence(self: "BooksHandler", sliced: list[dict]) -> float:
        """Calculate confidence score from top candidates."""
        if not sliced:
            return 0.0
        s1 = sliced[0]["score"]
        s2 = sliced[1]["score"] if len(sliced) > 1 else 0
        return max(0, min(1, s1 - 0.25 * s2))
