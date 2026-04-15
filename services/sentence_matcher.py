"""Condition-based sentence matching for structure-aware interpretation."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from data.stems import STEMS_BY_KOR
from services.sentence_filter import load_filtered_sentences

PRIMARY_PATTERN_ALIASES = {
    "식상격": {"식상격", "식상생재", "식상과다"},
    "재성격": {"재성격", "재다신약", "재성편중", "재약", "재생관"},
    "관성격": {"관성격", "관인상생", "관성강", "관살혼잡", "관성혼잡", "관성약"},
    "인성격": {"인성격", "인성과다"},
    "비겁격": {"비겁격", "비겁과다"},
}
PRIMARY_PATTERN_TO_CANONICAL = {
    alias: canonical for canonical, aliases in PRIMARY_PATTERN_ALIASES.items() for alias in aliases
}


def conditions_match(conditions: dict, analysis: dict) -> bool:
    """Return True when all condition keys match the analysis payload."""
    if not conditions:
        return True

    for key, expected in conditions.items():
        if _is_wildcard_expected(expected):
            continue

        if key.endswith("_contains"):
            source_key = key[: -len("_contains")]
            source_value = analysis.get(source_key)
            if not _contains_match(source_value, expected):
                return False
            continue

        if key == "day_master":
            if not _day_master_match(analysis.get("day_master"), expected):
                return False
            continue

        if key == "yongshin":
            if not _yongshin_match(analysis, expected):
                return False
            continue

        if key == "primary_pattern":
            if not _primary_pattern_match(analysis.get("primary_pattern"), expected):
                return False
            continue

        actual = analysis.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
            continue
        if actual != expected:
            return False
    return True


def compose_section(
    section_name: str,
    analysis: dict,
    sentence_db: list[dict],
    *,
    seed: int,
    base_count: int = 2,
    structure_count: int = 3,
    adjustment_count: int = 2,
    return_rows: bool = False,
) -> list[str] | tuple[list[str], list[dict], int]:
    """Build a section with base/structure/adjustment layering."""
    matched = [
        item
        for item in sentence_db
        if item.get("category") == section_name and conditions_match(item.get("conditions", {}), analysis)
    ]
    candidate_count = len(matched)
    matched.sort(
        key=lambda item: (
            int(item.get("priority", 0)),
            _condition_specificity(item.get("conditions", {})),
        ),
        reverse=True,
    )
    matched = _deduplicate_by_text(matched)

    selected: list[dict] = []
    selected.extend(_pick_from_type(matched, "base", base_count, seed + 7))
    selected.extend(_pick_from_type(matched, "structure", structure_count, seed + 13))
    selected.extend(_pick_from_type(matched, "adjustment", adjustment_count, seed + 19))

    selected = _deduplicate_by_text(selected)
    if not selected:
        if return_rows:
            return [], [], candidate_count
        return []

    # Fill shortages with top-ranked leftovers, still deterministic.
    if len(selected) < min(2, len(matched)):
        selected_ids = {item["id"] for item in selected if "id" in item}
        leftovers = [item for item in matched if item.get("id") not in selected_ids]
        selected.extend(_pick_spread(leftovers, min(2, len(matched)) - len(selected), seed + 23))
        selected = _deduplicate_by_text(selected)

    lines = [item["text"] for item in selected]
    if return_rows:
        return lines, selected, candidate_count
    return lines


def _contains_match(source_value, expected) -> bool:
    if source_value is None:
        return False
    expected_values = expected if isinstance(expected, list) else [expected]
    expected_values = [value for value in expected_values if not _is_wildcard_expected(value)]
    if not expected_values:
        return True

    if isinstance(source_value, str):
        return any(str(value) in source_value for value in expected_values)

    if isinstance(source_value, Iterable):
        normalized = [str(item) for item in source_value]
        return any(str(value) in normalized for value in expected_values)

    return any(str(value) == str(source_value) for value in expected_values)


def _deduplicate_by_text(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in items:
        text = item.get("text")
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(item)
    return deduped


def _pick_from_type(items: list[dict], item_type: str, count: int, seed: int) -> list[dict]:
    candidates = [item for item in items if item.get("type") == item_type]
    if not candidates or count <= 0:
        return []
    return _pick_spread(candidates, count, seed)


def _pick_spread(candidates: list[dict], count: int, seed: int) -> list[dict]:
    if not candidates or count <= 0:
        return []
    if len(candidates) <= count:
        return candidates[:]

    picked: list[dict] = []
    start = seed % len(candidates)
    step = 2 if len(candidates) > 2 else 1
    index = start
    visited: set[int] = set()

    while len(picked) < count and len(visited) < len(candidates):
        if index not in visited:
            picked.append(candidates[index])
            visited.add(index)
        index = (index + step) % len(candidates)
        if index in visited:
            index = (index + 1) % len(candidates)

    return picked[:count]


def _condition_specificity(conditions: dict) -> int:
    """Higher specificity means tighter branching and should be preferred."""
    if not conditions:
        return 0

    score = 0
    for key, value in conditions.items():
        if _is_wildcard_expected(value):
            continue
        score += 2 if key.endswith("_contains") else 1
        if isinstance(value, list):
            score += min(3, len(value))
    return score


def _is_wildcard_expected(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, list):
        return len([item for item in value if not _is_wildcard_expected(item)]) == 0
    return False


def _day_master_match(actual, expected) -> bool:
    if actual is None:
        return False
    expected_str = str(expected).strip().lower()
    actual_str = str(actual).strip().lower()
    if expected_str == actual_str:
        return True

    stem = str(actual).strip()
    if stem in STEMS_BY_KOR:
        element_kor = {"wood": "목", "fire": "화", "earth": "토", "metal": "금", "water": "수"}[STEMS_BY_KOR[stem]["element"]]
        if expected_str == f"{stem}{element_kor}".lower():
            return True
    return False


def _yongshin_match(analysis: dict, expected) -> bool:
    expected_str = str(expected).strip().lower()
    if expected_str == "":
        return True

    yongshin_display = str(analysis.get("yongshin", "")).strip().lower()
    if expected_str == yongshin_display:
        return True

    yongshin_element = str(analysis.get("yongshin_element", "")).strip().lower()
    return expected_str == yongshin_element


def _primary_pattern_match(actual, expected) -> bool:
    actual_key = _normalize_primary_pattern(actual)
    expected_key = _normalize_primary_pattern(expected)
    if expected_key == "":
        return True
    return actual_key == expected_key


def _normalize_primary_pattern(value) -> str:
    text = str(value or "").strip()
    if text == "":
        return ""
    return PRIMARY_PATTERN_TO_CANONICAL.get(text, text)


class SentenceMatcher:
    """DB-backed condition matcher for API/report usage."""

    def __init__(self, db_path: str = "data/sentences.json", db: list[dict] | None = None):
        if db is not None:
            self.db = db
            return

        if db_path == "data/sentences.json":
            self.db = load_filtered_sentences()
            return

        path = Path(db_path)
        if path.exists():
            self.db = json.loads(path.read_text(encoding="utf-8"))
        else:
            self.db = load_filtered_sentences()

    def match(self, analysis: dict, category: str, limit: int = 5) -> list[dict]:
        matched: list[dict] = []
        for row in self.db:
            if row.get("category") != category:
                continue
            if self.check_conditions(row.get("conditions", {}), analysis):
                matched.append(row)

        matched.sort(
            key=lambda row: (
                int(row.get("priority", 0)),
                int(row.get("quality_score", 0)),
                _condition_specificity(row.get("conditions", {})),
            ),
            reverse=True,
        )
        return matched[:limit]

    def check_conditions(self, conditions: dict, analysis: dict) -> bool:
        filtered: dict = {}
        for key, value in (conditions or {}).items():
            if key.endswith("_contains"):
                source_key = key[: -len("_contains")]
                if source_key not in analysis:
                    continue
                filtered[key] = value
                continue
            if key in {"day_master", "yongshin"} or key in analysis:
                filtered[key] = value
        return conditions_match(filtered, analysis)
