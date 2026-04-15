"""Rule helpers for the higher-quality interpretation engine."""

from __future__ import annotations

from data.stems import STEMS_BY_KOR
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
    counts = element_analysis.get("weighted_scores", element_analysis["elements"])
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


def _is_stem_target(target: str) -> bool:
    left = target.split("-")[0][:1] if target else ""
    if left in STEMS_BY_KOR:
        return True
    return any(left == item["hanja"] for item in STEMS_BY_KOR.values())


def _is_branch_pressure_item(item: dict) -> bool:
    if item.get("type") not in {"충", "형"}:
        return False
    return not _is_stem_target(str(item.get("target", "")))


def build_analysis_flags(
    *,
    saju: dict,
    element_analysis: dict,
    strength_analysis: dict,
    yongshin_analysis: dict,
    interaction_analysis: dict,
    ten_god_analysis: dict,
) -> dict:
    """Build reusable rule flags from the intermediate domain-analysis layer."""
    day_element = STEMS_BY_KOR[saju["day"]["stem"]]["element"]
    month_branch = saju["month"]["branch"]
    dominant = element_analysis["dominant"]
    weak = element_analysis["weak"]
    hidden_groups = ten_god_analysis.get("hidden_ten_god_groups", [])

    return {
        "is_day_master_strong": strength_analysis["label"] in {"strong", "slightly_strong"},
        "is_day_master_weak": strength_analysis["label"] in {"weak", "slightly_weak"},
        "is_balanced_structure": strength_analysis["label"] == "balanced",
        "needs_resource_support": yongshin_analysis["primary_candidate"] == strength_analysis["resource_element"],
        "needs_output_release": yongshin_analysis["primary_candidate"] == strength_analysis["output_element"],
        "dominant_element": dominant[0],
        "weak_element": weak[0],
        "day_element": day_element,
        "month_branch": month_branch,
        "has_branch_conflict": any(item["type"] in {"충", "형", "파", "해", "원진"} for item in interaction_analysis["natal"]),
        "has_natal_conflict": any(item["type"] in {"충", "형", "파", "해", "원진"} for item in interaction_analysis["natal"]),
        "has_natal_harmony": any(item["type"] == "합" for item in interaction_analysis["natal"]),
        "has_luck_pressure": any(
            _is_branch_pressure_item(item) for key in ("with_daewoon", "with_yearly", "with_daily") for item in interaction_analysis[key]
        ),
        "wealth_flow_open": any(group == "재성" for group in hidden_groups)
        or ten_god_analysis["ten_gods"].get("month") in {"편재", "정재"},
        "officer_pressure_high": strength_analysis["officer_pressure"] >= strength_analysis["resource_support"],
        "hidden_group_focus": hidden_groups[0] if hidden_groups else None,
        "month_visible_ten_god": ten_god_analysis["ten_gods"].get("month"),
    }
