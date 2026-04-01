"""Ten-gods calculation based on the day stem."""

from __future__ import annotations

from data.stems import STEMS_BY_KOR
from data.ten_gods_labels import TEN_GOD_DETAILS, TEN_GOD_LABELS
from data.ten_gods_map import TEN_GODS_MAP
from services.interpretation_engine import select_ten_god_explanation

GENERATES = {
    "wood": "fire",
    "fire": "earth",
    "earth": "metal",
    "metal": "water",
    "water": "wood",
}

CONTROLS = {
    "wood": "earth",
    "fire": "metal",
    "earth": "water",
    "metal": "wood",
    "water": "fire",
}


def calculate_ten_gods(saju: dict) -> dict:
    """Calculate ten gods for year/month/time heavenly stems."""
    day_stem = STEMS_BY_KOR[saju["day"]["stem"]]

    result = {}
    labels = {}
    details = {}
    explanations = {}
    for pillar_name in ["year", "month", "time"]:
        pillar = saju[pillar_name]
        result[pillar_name] = None if pillar is None else _calculate_single(day_stem, pillar["stem"])
        labels[pillar_name] = None if result[pillar_name] is None else TEN_GOD_LABELS[result[pillar_name]]
        details[pillar_name] = None if result[pillar_name] is None else TEN_GOD_DETAILS[result[pillar_name]]
        explanations[pillar_name] = (
            None if result[pillar_name] is None else select_ten_god_explanation(result[pillar_name], len(pillar_name))
        )

    return {
        "ten_gods": result,
        "ten_gods_labels": labels,
        "ten_gods_details": details,
        "ten_gods_explanations": explanations,
    }


def calculate_ten_god_for_stem(day_stem_kor: str, target_stem_kor: str | None) -> str | None:
    """Calculate a single ten-god label from the day stem and another stem."""
    if target_stem_kor is None:
        return None

    day_stem = STEMS_BY_KOR[day_stem_kor]
    return _calculate_single(day_stem, target_stem_kor)


def _calculate_single(day_stem: dict, target_stem_kor: str) -> str:
    target_stem = STEMS_BY_KOR[target_stem_kor]
    relation = _resolve_relation(day_stem["element"], target_stem["element"])
    polarity = "same" if day_stem["yin_yang"] == target_stem["yin_yang"] else "opposite"
    return TEN_GODS_MAP[relation][polarity]


def _resolve_relation(day_element: str, target_element: str) -> str:
    if day_element == target_element:
        return "same"
    if GENERATES[day_element] == target_element:
        return "output"
    if CONTROLS[day_element] == target_element:
        return "wealth"
    if CONTROLS[target_element] == day_element:
        return "officer"
    if GENERATES[target_element] == day_element:
        return "resource"
    raise ValueError(f"Unknown ten-gods relation: {day_element} -> {target_element}")
