"""Five-elements analysis for saju pillars."""

from __future__ import annotations

from collections import Counter

from data.branches import BRANCHES_BY_KOR
from data.stems import STEMS_BY_KOR

ELEMENT_ORDER = ["wood", "fire", "earth", "metal", "water"]
ELEMENT_KOR = {
    "wood": "목",
    "fire": "화",
    "earth": "토",
    "metal": "금",
    "water": "수",
}


def analyze_elements(saju: dict) -> dict:
    """Count visible stem/branch elements without hidden stems."""
    counter = Counter({element: 0 for element in ELEMENT_ORDER})

    for pillar in saju.values():
        if pillar is None:
            continue
        counter[STEMS_BY_KOR[pillar["stem"]]["element"]] += 1
        counter[BRANCHES_BY_KOR[pillar["branch"]]["element"]] += 1

    dominant = _pick_dominant(counter)
    weak = _pick_weak(counter)

    return {
        "elements": {element: counter[element] for element in ELEMENT_ORDER},
        "dominant": dominant,
        "weak": weak,
        "dominant_kor": [ELEMENT_KOR[element] for element in dominant],
        "weak_kor": [ELEMENT_KOR[element] for element in weak],
    }


def _pick_dominant(counter: Counter) -> list[str]:
    highest = max(counter[element] for element in ELEMENT_ORDER)
    return [element for element in ELEMENT_ORDER if counter[element] == highest]


def _pick_weak(counter: Counter) -> list[str]:
    lowest = min(counter[element] for element in ELEMENT_ORDER)
    return [element for element in ELEMENT_ORDER if counter[element] == lowest]
