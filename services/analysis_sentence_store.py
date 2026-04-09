"""Load structured interpretation sentence pools from JSON."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "analysis_sentences.json"

CATEGORY_EXPANSIONS = {
    "social_reaction": (
        "실제 사람 사이에서는 ",
        "협력과 갈등 장면에서는 ",
        "관계가 깊어질수록 ",
    ),
    "speech_style": (
        "표현 방식으로는 ",
        "대화 장면에서는 ",
        "말을 풀어낼 때는 ",
    ),
    "base_personality": (
        "기본 성향을 더 풀어보면 ",
        "생활 리듬으로 옮기면 ",
        "평소 결을 보면 ",
    ),
    "work_adaptation": (
        "실제 업무 환경에서는 ",
        "조직 안에서는 ",
        "직장 적응 방식으로는 ",
    ),
    "money_habit": (
        "재정 습관으로 옮기면 ",
        "생활 재무 쪽에서는 ",
        "돈 흐름을 다룰 때는 ",
    ),
    "first_impression": (
        "겉으로 보이는 인상은 ",
        "처음 만난 사람 입장에서는 ",
        "외부 평판 쪽으로는 ",
    ),
    "intimate_reaction": (
        "가까운 관계 안에서는 ",
        "가족이나 연인 앞에서는 ",
        "정서적으로 가까워질수록 ",
    ),
    "personality_modifier": (
        "이 흐름을 성격 쪽으로 풀면 ",
        "성향 보정으로 읽으면 ",
        "실제 판단 습관으로는 ",
    ),
    "career_modifier": (
        "직업 흐름 보정으로는 ",
        "실무 방향으로 읽으면 ",
        "커리어 해석에선 ",
    ),
    "wealth_modifier": (
        "재물 흐름 보정으로는 ",
        "돈 문제로 옮기면 ",
        "재정 운영 쪽으로는 ",
    ),
    "action_advice": (
        "실행 조언으로 옮기면 ",
        "현실 적용 기준으로는 ",
        "지금 흐름에서는 ",
    ),
}

ENDING_REWRITES = (
    ("편입니다.", "경향이 비교적 또렷합니다."),
    ("편입니다.", "쪽으로 흐를 가능성이 큽니다."),
    ("중요합니다.", "핵심 포인트가 되기 쉽습니다."),
    ("도움이 됩니다.", "실제 체감 차이를 만드는 편입니다."),
    ("좋습니다.", "더 유리하게 작동할 수 있습니다."),
)


def _expand_sentence(sentence: str, category: str) -> list[str]:
    results = [sentence.strip()]
    for prefix in CATEGORY_EXPANSIONS.get(category, ()):
        results.append(f"{prefix}{sentence.strip()}")
    for source, target in ENDING_REWRITES:
        if sentence.endswith(source):
            results.append(f"{sentence[:-len(source)]}{target}")
    deduped: list[str] = []
    seen: set[str] = set()
    for item in results:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        deduped.append(cleaned)
        seen.add(cleaned)
    return deduped


def _expand_node(node: Any, category: str | None = None) -> Any:
    if isinstance(node, list):
        expanded: list[str] = []
        seen: set[str] = set()
        for item in node:
            for candidate in _expand_sentence(item, category or ""):
                if candidate in seen:
                    continue
                expanded.append(candidate)
                seen.add(candidate)
        return expanded
    if isinstance(node, dict):
        return {key: _expand_node(value, key) for key, value in node.items()}
    return node


@lru_cache(maxsize=1)
def load_analysis_sentences() -> dict:
    """Return cached sentence pools for high-density interpretation branching."""
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return _expand_node(raw)
