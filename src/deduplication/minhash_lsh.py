"""MinHash and Locality Sensitive Hashing (LSH) near-duplicate detection engine."""

from __future__ import annotations

import re
from typing import Iterable

from datasketch import MinHash, MinHashLSH
from models.news import NewsItem


def normalize_text(text: str) -> str:
    """Normalize text by lowering, stripping URLs, and removing special characters."""
    if not text:
        return ""
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Lowercase
    text = text.lower()
    # Replace punctuation with spaces
    text = re.sub(r"[^\w\s]", " ", text)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


def get_shingles(text: str, k: int = 3) -> set[str]:
    """
    Generate word k-grams (shingles) from normalized text.
    If text has fewer than k words, fallback to individual words or character 3-grams.
    """
    normalized = normalize_text(text)
    words = normalized.split()

    if len(words) >= k:
        return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}

    if words:
        return set(words)

    # Character shingles fallback for very short strings
    if len(normalized) >= 3:
        return {normalized[i : i + 3] for i in range(len(normalized) - 2)}

    return {normalized} if normalized else set()


def create_minhash(text: str, num_perm: int = 128) -> MinHash:
    """Create a MinHash signature from input text."""
    minhash = MinHash(num_perm=num_perm)
    shingles = get_shingles(text)

    for shingle in shingles:
        minhash.update(shingle.encode("utf-8"))

    return minhash


class NewsDeduplicator:
    """
    In-memory MinHash LSH deduplication index.
    Quickly identifies identical and near-duplicate articles (> 75% similarity).
    """

    def __init__(self, threshold: float = 0.75, num_perm: int = 128) -> None:
        self.threshold = threshold
        self.num_perm = num_perm
        self.lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
        self.indexed_items: dict[str, NewsItem] = {}
        self.minhashes: dict[str, MinHash] = {}

    def _get_item_text(self, item: NewsItem) -> str:
        """Combine title and description for richer duplicate comparison."""
        parts = [item.title]
        if item.description:
            parts.append(item.description)
        return " ".join(parts)

    def check_duplicate(self, item: NewsItem) -> str | None:
        """
        Query LSH index for near duplicates of the given item.
        Returns the ID of the matched parent article if found, else None.
        """
        text = self._get_item_text(item)
        minhash = create_minhash(text, num_perm=self.num_perm)

        candidates = self.lsh.query(minhash)

        # Exact ID match is the item itself
        candidates = [c for c in candidates if c != item.id]

        if not candidates:
            return None

        # Return the best matching candidate (highest Jaccard similarity)
        best_candidate = None
        best_score = 0.0

        for candidate_id in candidates:
            if candidate_id in self.minhashes:
                score = minhash.jaccard(self.minhashes[candidate_id])
                if score >= self.threshold and score > best_score:
                    best_score = score
                    best_candidate = candidate_id

        return best_candidate

    def add_item(self, item: NewsItem) -> NewsItem:
        """
        Process a single NewsItem.
        If it is a duplicate, updates its is_duplicate and duplicate_of fields.
        If it is unique, indexes it in the LSH table.
        """
        duplicate_of = self.check_duplicate(item)

        if duplicate_of:
            item.is_duplicate = True
            item.duplicate_of = duplicate_of
        else:
            item.is_duplicate = False
            item.duplicate_of = None

            # Index new original item
            text = self._get_item_text(item)
            minhash = create_minhash(text, num_perm=self.num_perm)

            try:
                self.lsh.insert(item.id, minhash)
                self.indexed_items[item.id] = item
                self.minhashes[item.id] = minhash
            except ValueError:
                # Key already in LSH index
                pass

        return item

    def deduplicate_batch(
        self, items: Iterable[NewsItem]
    ) -> tuple[list[NewsItem], list[NewsItem]]:
        """
        Deduplicate a stream/batch of items.
        Returns a tuple of (unique_items, duplicate_items).
        """
        uniques: list[NewsItem] = []
        duplicates: list[NewsItem] = []

        for item in items:
            processed = self.add_item(item)
            if processed.is_duplicate:
                duplicates.append(processed)
            else:
                uniques.append(processed)

        return uniques, duplicates
