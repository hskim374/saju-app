"""Ten-gods calculation based on the day stem."""

from __future__ import annotations

from collections import Counter

from data.hidden_stems import get_hidden_stems
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

TEN_GOD_GROUPS = {
    "비견": "비겁",
    "겁재": "비겁",
    "식신": "식상",
    "상관": "식상",
    "편재": "재성",
    "정재": "재성",
    "편관": "관성",
    "정관": "관성",
    "편인": "인성",
    "정인": "인성",
}

KINSHIP_BY_TEN_GOD = {
    "비견": "형제자매/동료",
    "겁재": "경쟁자/동료",
    "식신": "자녀/결과물",
    "상관": "자녀/표현 압력",
    "편재": "재물/아버지/남성 배우자 별",
    "정재": "재물/생활 기반/남성 배우자 별",
    "편관": "압박/규범/여성 배우자 별",
    "정관": "직위/책임/여성 배우자 별",
    "편인": "보호/어머니/직관",
    "정인": "보호/어머니/학습",
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
    hidden = calculate_hidden_ten_gods(saju)
    visible_map = {
        "year_stem": result["year"],
        "month_stem": result["month"],
        "time_stem": result["time"],
    }
    month_branch_hidden = hidden["hidden_ten_gods"].get("month", [])

    return {
        "ten_gods": result,
        "visible": visible_map,
        "visible_ten_gods": visible_map,
        "ten_gods_labels": labels,
        "ten_gods_details": details,
        "ten_gods_explanations": explanations,
        "hidden": {
            "year_branch": hidden["hidden_ten_gods"].get("year", []),
            "month_branch": hidden["hidden_ten_gods"].get("month", []),
            "day_branch": hidden["hidden_ten_gods"].get("day", []),
            "time_branch": hidden["hidden_ten_gods"].get("time", []),
        },
        "hidden_ten_gods": hidden["hidden_ten_gods"],
        "month_focus_ten_gods": {
            "month_stem": result["month"],
            "month_branch": month_branch_hidden,
        },
        "hidden_ten_god_groups": hidden["hidden_ten_god_groups"],
        "dominant_groups": hidden["hidden_ten_god_groups"],
        "kinship_mapping": hidden["kinship_mapping"],
    }


def calculate_ten_god_for_stem(day_stem_kor: str, target_stem_kor: str | None) -> str | None:
    """Calculate a single ten-god label from the day stem and another stem."""
    if target_stem_kor is None:
        return None

    day_stem = STEMS_BY_KOR[day_stem_kor]
    return _calculate_single(day_stem, target_stem_kor)


def calculate_hidden_ten_gods(saju: dict) -> dict:
    """Calculate hidden-stem ten gods for each branch."""
    day_stem_kor = saju["day"]["stem"]
    hidden_ten_gods: dict[str, list[str]] = {}
    group_counter: Counter[str] = Counter()

    for pillar_name in ["year", "month", "day", "time"]:
        pillar = saju.get(pillar_name)
        if pillar is None:
            hidden_ten_gods[pillar_name] = []
            continue
        values: list[str] = []
        for hidden in get_hidden_stems(pillar["branch"]):
            ten_god = calculate_ten_god_for_stem(day_stem_kor, hidden["stem"])
            if ten_god is None:
                continue
            values.append(ten_god)
            group_counter[TEN_GOD_GROUPS[ten_god]] += float(hidden["weight"])
        hidden_ten_gods[pillar_name] = values

    max_weight = max(group_counter.values()) if group_counter else 0
    hidden_groups = [
        group
        for group, score in sorted(group_counter.items(), key=lambda item: (-item[1], item[0]))
        if max_weight and abs(score - max_weight) < 0.01
    ]
    return {
        "hidden_ten_gods": hidden_ten_gods,
        "hidden_ten_god_groups": hidden_groups,
        "kinship_mapping": {
            "visible": {
                pillar_name: None if ten_god is None else KINSHIP_BY_TEN_GOD[ten_god]
                for pillar_name, ten_god in {
                    "year_stem": calculate_ten_god_for_stem(day_stem_kor, saju["year"]["stem"]),
                    "month_stem": calculate_ten_god_for_stem(day_stem_kor, saju["month"]["stem"]),
                    "time_stem": calculate_ten_god_for_stem(day_stem_kor, saju["time"]["stem"]) if saju.get("time") else None,
                }.items()
            },
            "hidden": {
                pillar_name: [KINSHIP_BY_TEN_GOD[value] for value in values]
                for pillar_name, values in hidden_ten_gods.items()
            },
            "spouse_star_rules": {
                "male": "재성(편재/정재)을 배우자 별로 봅니다.",
                "female": "관성(편관/정관)을 배우자 별로 봅니다.",
            },
        },
    }


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
