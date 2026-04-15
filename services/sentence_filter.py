"""Sentence filtering pipeline: dedupe + quality scoring + save/load helpers."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

RAW_SENTENCE_DB_PATHS = [
    Path("data/structured_sentence_db.json"),
    Path("data/structured_sentence_db_extra.json"),
]
FILTERED_SENTENCE_DB_PATH = Path("data/sentences.json")

ABSTRACT_WORDS = {"좋다", "나쁘다", "대체로", "어느 정도"}
SPECIFIC_KEYWORDS = {
    "관계",
    "직장",
    "돈",
    "선택",
    "결정",
    "일정",
    "지출",
    "수익",
    "건강",
    "마감",
}

TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]+")


class SentenceFilter:
    """Filter generated sentence DB into deterministic, higher-quality subsets."""

    def remove_duplicates(self, sentences: list[dict], threshold: float = 0.85) -> list[dict]:
        if len(sentences) <= 1:
            return sentences[:]

        texts = [item.get("text", "") for item in sentences]
        similarity_matrix = _cosine_similarity_matrix(texts)

        keep: list[dict] = []
        removed: set[int] = set()
        for idx in range(len(texts)):
            if idx in removed:
                continue
            keep.append(sentences[idx])
            for jdx in range(idx + 1, len(texts)):
                if similarity_matrix[idx][jdx] > threshold:
                    removed.add(jdx)
        return keep

    def score_sentence(self, sentence: dict) -> int:
        text = str(sentence.get("text", "")).strip()
        if not text:
            return 0

        score = 0
        if 20 <= len(text) <= 60:
            score += 20

        if not any(word in text for word in ABSTRACT_WORDS):
            score += 20

        if any(word in text for word in SPECIFIC_KEYWORDS):
            score += 30

        conditions = sentence.get("conditions") or {}
        if isinstance(conditions, dict) and any(str(value).strip() != "" for value in conditions.values()):
            score += 30

        return score

    def filter_pipeline(self, sentences: list[dict], threshold: float = 0.85, min_quality: int = 60) -> list[dict]:
        deduped = self.remove_duplicates(sentences, threshold=threshold)
        scored: list[dict] = []
        for item in deduped:
            cloned = dict(item)
            cloned["quality_score"] = self.score_sentence(cloned)
            scored.append(cloned)
        filtered = [item for item in scored if item["quality_score"] >= min_quality]
        filtered.sort(
            key=lambda item: (
                int(item.get("quality_score", 0)),
                int(item.get("priority", 0)),
                str(item.get("id", "")),
            ),
            reverse=True,
        )
        return filtered

    def save_sentences(self, sentences: list[dict], output_path: Path = FILTERED_SENTENCE_DB_PATH) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(sentences, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    def filter_and_save(
        self,
        *,
        threshold: float = 0.85,
        min_quality: int = 60,
        output_path: Path = FILTERED_SENTENCE_DB_PATH,
    ) -> dict:
        raw = load_sentence_sources()
        refined = self.filter_pipeline(raw, threshold=threshold, min_quality=min_quality)
        saved_path = self.save_sentences(refined, output_path=output_path)
        return {
            "input_count": len(raw),
            "output_count": len(refined),
            "removed_count": len(raw) - len(refined),
            "output_path": str(saved_path),
            "threshold": threshold,
            "min_quality": min_quality,
        }


def load_sentence_sources(paths: list[Path] | None = None) -> list[dict]:
    source_paths = paths or RAW_SENTENCE_DB_PATHS
    merged: list[dict] = []
    seen_ids: set[str] = set()

    for path in source_paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload:
            row_id = str(row.get("id", "")).strip()
            if row_id and row_id in seen_ids:
                continue
            merged.append(row)
            if row_id:
                seen_ids.add(row_id)
    return merged


def load_filtered_sentences() -> list[dict]:
    filtered: list[dict] = []
    if FILTERED_SENTENCE_DB_PATH.exists():
        payload = json.loads(FILTERED_SENTENCE_DB_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, list) and payload:
            filtered = payload

    if not filtered:
        raw = load_sentence_sources()
        filtered = SentenceFilter().filter_pipeline(raw)

    # Keep all raw rows available at runtime even if filtered out.
    source_rows = load_sentence_sources(paths=RAW_SENTENCE_DB_PATHS)
    return _merge_rows_by_id(filtered, source_rows)


def _merge_rows_by_id(primary: list[dict], extras: list[dict]) -> list[dict]:
    merged = list(primary)
    seen_ids = {str(row.get("id", "")).strip() for row in merged if str(row.get("id", "")).strip()}

    for row in extras:
        row_id = str(row.get("id", "")).strip()
        if row_id and row_id in seen_ids:
            continue
        merged.append(row)
        if row_id:
            seen_ids.add(row_id)

    return merged


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _tfidf_vectors(texts: list[str]) -> tuple[list[dict[int, float]], dict[str, int]]:
    tokenized = [_tokenize(text) for text in texts]
    vocabulary: dict[str, int] = {}
    doc_freq: dict[str, int] = {}

    for tokens in tokenized:
        seen: set[str] = set()
        for token in tokens:
            if token not in vocabulary:
                vocabulary[token] = len(vocabulary)
            if token not in seen:
                doc_freq[token] = doc_freq.get(token, 0) + 1
                seen.add(token)

    total_docs = len(texts)
    vectors: list[dict[int, float]] = []
    for tokens in tokenized:
        if not tokens:
            vectors.append({})
            continue
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        length = len(tokens)
        vector: dict[int, float] = {}
        for token, count in counts.items():
            tf = count / length
            idf = math.log((1 + total_docs) / (1 + doc_freq[token])) + 1.0
            vector[vocabulary[token]] = tf * idf
        vectors.append(vector)
    return vectors, vocabulary


def _vector_cosine(left: dict[int, float], right: dict[int, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(left[idx] * right.get(idx, 0.0) for idx in left)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _cosine_similarity_matrix(texts: list[str]) -> list[list[float]]:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        matrix = TfidfVectorizer().fit_transform(texts)
        sim = cosine_similarity(matrix)
        return [[float(value) for value in row] for row in sim]
    except Exception:
        vectors, _ = _tfidf_vectors(texts)
        size = len(vectors)
        matrix = [[0.0 for _ in range(size)] for _ in range(size)]
        for idx in range(size):
            matrix[idx][idx] = 1.0
            for jdx in range(idx + 1, size):
                value = _vector_cosine(vectors[idx], vectors[jdx])
                matrix[idx][jdx] = value
                matrix[jdx][idx] = value
        return matrix
