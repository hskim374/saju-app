"""Rule helpers for the higher-quality interpretation engine."""

from __future__ import annotations

from services.interpretation_templates import ELEMENT_COMBO_STORIES, ELEMENT_KOR, ELEMENT_MEANINGS


def build_seed(*values: object) -> int:
    return sum(ord(char) for value in values for char in str(value))


def join_elements(elements: list[str]) -> str:
    return ", ".join(ELEMENT_KOR[element] for element in elements)


def dominant_story(dominant: list[str], seed: int) -> str:
    if len(dominant) >= 2:
        combo = frozenset(dominant[:3])
        if combo in ELEMENT_COMBO_STORIES:
            options = ELEMENT_COMBO_STORIES[combo]
            return options[seed % len(options)]
    return f"{join_elements(dominant)} 기운이 중심이 되어 {ELEMENT_MEANINGS[dominant[0]]}이 먼저 작동하는 편입니다."


def pick_support_elements(element_analysis: dict) -> list[str]:
    counts = element_analysis["elements"]
    dominant = set(element_analysis["dominant"])
    ranked = sorted(
        ((element, count) for element, count in counts.items() if element not in dominant and count > 0),
        key=lambda item: (-item[1], item[0]),
    )
    if not ranked:
        return element_analysis["dominant"][:1]
    best_count = ranked[0][1]
    return [element for element, count in ranked if count == best_count]


def weak_level(elements: dict, weak_element: str) -> str:
    count = elements[weak_element]
    if count == 0:
        return "strong"
    if count == 1:
        return "medium"
    return "light"


def element_meaning(element: str) -> str:
    return ELEMENT_MEANINGS[element]


def first_focus(values: list[str], default: str) -> str:
    return values[0] if values else default
