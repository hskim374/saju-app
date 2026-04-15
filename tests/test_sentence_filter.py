"""Tests for sentence filtering and API integration endpoints."""

import asyncio

from main import api_result
from services.sentence_filter import SentenceFilter, load_filtered_sentences
from services.sentence_matcher import SentenceMatcher


def test_sentence_filter_pipeline_removes_duplicates_and_low_quality_rows():
    rows = [
        {
            "id": "t1",
            "category": "personality",
            "type": "base",
            "priority": 90,
            "conditions": {"season": "winter"},
            "text": "관계와 직장 선택 기준을 먼저 정하면 결정 피로를 줄일 수 있습니다.",
        },
        {
            "id": "t2",
            "category": "personality",
            "type": "base",
            "priority": 80,
            "conditions": {"season": "winter"},
            "text": "관계와 직장 선택 기준을 먼저 정하면 결정 피로를 줄일 수 있습니다.",
        },
        {
            "id": "t3",
            "category": "personality",
            "type": "base",
            "priority": 50,
            "conditions": {},
            "text": "대체로 좋다.",
        },
    ]

    filtered = SentenceFilter().filter_pipeline(rows, threshold=0.8, min_quality=60)

    assert len(filtered) == 1
    assert filtered[0]["id"] == "t1"
    assert filtered[0]["quality_score"] >= 60


def test_api_result_endpoint_returns_analysis_and_report_sections():
    payload = asyncio.run(
        api_result(
            {
                "year": {"stem": "신", "branch": "묘"},
                "month": {"stem": "임", "branch": "진"},
                "day": {"stem": "임", "branch": "술"},
                "time": {"stem": "경", "branch": "진"},
            }
        )
    )

    assert payload["analysis"]["day_master"] == "임"
    assert payload["analysis"]["season"] in {"spring", "summer", "autumn", "winter"}
    assert "personality" in payload["report"]
    assert "career" in payload["report"]


def test_sentence_matcher_normalizes_primary_pattern_aliases():
    matcher = SentenceMatcher(
        db=[
            {
                "id": "alias_1",
                "category": "career",
                "type": "structure",
                "priority": 90,
                "conditions": {"primary_pattern": "식상생재"},
                "text": "식상생재 별칭 매칭 문장",
            }
        ]
    )

    matched = matcher.match({"primary_pattern": "식상격"}, "career", limit=5)

    assert len(matched) == 1
    assert matched[0]["id"] == "alias_1"


def test_load_filtered_sentences_keeps_legacy_rows_available():
    rows = load_filtered_sentences()
    ids = {row.get("id") for row in rows}

    # legacy rows that were previously filtered out should remain selectable.
    assert "action_base_001" in ids
    assert "core_base_001" in ids


def test_load_filtered_sentences_covers_core_condition_gaps():
    rows = load_filtered_sentences()

    values: dict[str, set] = {
        "day_master": set(),
        "strength_label": set(),
        "yongshin": set(),
    }
    for row in rows:
        conditions = row.get("conditions") or {}
        for key in values:
            if key not in conditions:
                continue
            value = conditions.get(key)
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    continue
            values[key].add(value)

    assert {"slightly_strong", "slightly_weak"}.issubset(values["strength_label"])
    assert {"metal", "earth"}.issubset(values["yongshin"])
    assert {"갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"}.issubset(values["day_master"])
