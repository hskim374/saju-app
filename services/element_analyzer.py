"""Five-elements analysis for saju pillars."""

from __future__ import annotations

from collections import Counter

from data.branches import BRANCHES_BY_KOR
from data.hidden_stems import get_hidden_stems
from data.stems import STEMS_BY_KOR

ELEMENT_ORDER = ["wood", "fire", "earth", "metal", "water"]
ELEMENT_KOR = {
    "wood": "목",
    "fire": "화",
    "earth": "토",
    "metal": "금",
    "water": "수",
}

SEASON_FACTORS_BY_MONTH_BRANCH = {
    "인": {"wood": 1.25, "fire": 1.08, "earth": 0.95, "metal": 0.82, "water": 0.92},
    "묘": {"wood": 1.28, "fire": 1.08, "earth": 0.92, "metal": 0.8, "water": 0.9},
    "진": {"wood": 1.05, "fire": 1.02, "earth": 1.18, "metal": 0.9, "water": 0.92},
    "사": {"wood": 0.92, "fire": 1.25, "earth": 1.05, "metal": 0.86, "water": 0.78},
    "오": {"wood": 0.88, "fire": 1.28, "earth": 1.08, "metal": 0.82, "water": 0.74},
    "미": {"wood": 0.92, "fire": 1.02, "earth": 1.2, "metal": 0.9, "water": 0.82},
    "신": {"wood": 0.8, "fire": 0.9, "earth": 1.0, "metal": 1.24, "water": 1.05},
    "유": {"wood": 0.78, "fire": 0.88, "earth": 0.98, "metal": 1.28, "water": 1.08},
    "술": {"wood": 0.88, "fire": 0.98, "earth": 1.18, "metal": 1.02, "water": 0.88},
    "해": {"wood": 1.0, "fire": 0.8, "earth": 0.9, "metal": 1.02, "water": 1.24},
    "자": {"wood": 1.02, "fire": 0.78, "earth": 0.88, "metal": 1.05, "water": 1.28},
    "축": {"wood": 0.88, "fire": 0.82, "earth": 1.18, "metal": 1.0, "water": 1.08},
}


def analyze_elements_with_hidden(
    saju: dict,
    *,
    include_hidden: bool = True,
    include_season_weight: bool = True,
) -> dict:
    """Count visible elements and build a richer weighted balance model."""
    visible_counter = Counter({element: 0.0 for element in ELEMENT_ORDER})
    hidden_counter = Counter({element: 0.0 for element in ELEMENT_ORDER})

    for pillar in saju.values():
        if pillar is None:
            continue
        visible_counter[STEMS_BY_KOR[pillar["stem"]]["element"]] += 1
        visible_counter[BRANCHES_BY_KOR[pillar["branch"]]["element"]] += 1
        if include_hidden:
            for hidden in get_hidden_stems(pillar["branch"]):
                hidden_element = STEMS_BY_KOR[hidden["stem"]]["element"]
                hidden_counter[hidden_element] += float(hidden["weight"])

    season_factor = (
        _season_factor_for_month_branch(saju["month"]["branch"])
        if include_season_weight
        else {element: 1.0 for element in ELEMENT_ORDER}
    )
    weighted_scores = {
        element: round((visible_counter[element] + hidden_counter[element]) * season_factor[element], 2)
        for element in ELEMENT_ORDER
    }
    dominant = _pick_dominant(weighted_scores)
    weak = _pick_weak(weighted_scores)
    support = _pick_support(weighted_scores, dominant)
    visible_counts = {element: int(visible_counter[element]) for element in ELEMENT_ORDER}
    hidden_counts = {element: round(hidden_counter[element], 2) for element in ELEMENT_ORDER}

    return {
        "elements": visible_counts,
        "raw_counts": visible_counts,
        "visible_counts": visible_counts,
        "hidden_counts": hidden_counts,
        "season_factor": season_factor,
        "seasonal_factor": season_factor,
        "weighted_scores": weighted_scores,
        "dominant": dominant,
        "weak": weak,
        "support": support,
        "dominant_kor": [ELEMENT_KOR[element] for element in dominant],
        "weak_kor": [ELEMENT_KOR[element] for element in weak],
        "support_kor": [ELEMENT_KOR[element] for element in support],
    }


def analyze_elements(saju: dict) -> dict:
    """Backward-compatible element analysis entry point."""
    return analyze_elements_with_hidden(saju)


def _season_factor_for_month_branch(month_branch: str) -> dict[str, float]:
    return SEASON_FACTORS_BY_MONTH_BRANCH[month_branch]


def _pick_dominant(scores: dict[str, float]) -> list[str]:
    highest = max(scores[element] for element in ELEMENT_ORDER)
    return [element for element in ELEMENT_ORDER if abs(scores[element] - highest) < 0.01]


def _pick_weak(scores: dict[str, float]) -> list[str]:
    lowest = min(scores[element] for element in ELEMENT_ORDER)
    return [element for element in ELEMENT_ORDER if abs(scores[element] - lowest) < 0.01]


def _pick_support(scores: dict[str, float], dominant: list[str]) -> list[str]:
    ranked = [
        (element, value)
        for element, value in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        if element not in dominant
    ]
    if not ranked:
        return dominant[:1]
    best_score = ranked[0][1]
    return [element for element, value in ranked if abs(value - best_score) < 0.01]
