"""Day-master strength scoring based on weighted element balance."""

from __future__ import annotations

from data.stems import STEMS_BY_KOR

ELEMENT_LABELS = {
    "wood": "목(木)",
    "fire": "화(火)",
    "earth": "토(土)",
    "metal": "금(金)",
    "water": "수(水)",
}

GENERATES = {
    "wood": "fire",
    "fire": "earth",
    "earth": "metal",
    "metal": "water",
    "water": "wood",
}


def calculate_strength_analysis(saju: dict, element_analysis: dict) -> dict:
    """Calculate a simple but explainable day-master strength model."""
    day_stem = saju["day"]["stem"]
    day_element = STEMS_BY_KOR[day_stem]["element"]
    weighted_scores = element_analysis["weighted_scores"]
    season_factor = element_analysis["season_factor"]

    same_element = day_element
    resource_element = _resource_element(day_element)
    output_element = GENERATES[day_element]
    wealth_element = _wealth_element(day_element)
    officer_element = _officer_element(day_element)

    same_support = weighted_scores[same_element] * 1.25
    resource_support = weighted_scores[resource_element] * 1.05
    output_drain = weighted_scores[output_element] * 0.8
    wealth_pressure = weighted_scores[wealth_element] * 0.95
    officer_pressure = weighted_scores[officer_element] * 1.0
    season_support = (season_factor[day_element] - 1.0) * 12

    raw_balance = same_support + resource_support - output_drain - wealth_pressure - officer_pressure + season_support
    score = max(1, min(99, round(50 + raw_balance * 8)))
    label, display_label = _strength_label(score)

    key_reasons = _build_reason_lines(
        day_element=day_element,
        resource_element=resource_element,
        output_element=output_element,
        wealth_element=wealth_element,
        officer_element=officer_element,
        weighted_scores=weighted_scores,
        season_factor=season_factor,
        same_support=same_support,
        resource_support=resource_support,
        output_drain=output_drain,
        wealth_pressure=wealth_pressure,
        officer_pressure=officer_pressure,
    )

    return {
        "score": score,
        "strength_score": score,
        "label": label,
        "strength_label": label,
        "display_label": display_label,
        "day_master": day_stem,
        "day_element": day_element,
        "same_element": same_element,
        "resource_element": resource_element,
        "output_element": output_element,
        "wealth_element": wealth_element,
        "officer_element": officer_element,
        "season_support": round(season_support, 2),
        "same_element_support": round(same_support, 2),
        "resource_support": round(resource_support, 2),
        "output_drain": round(output_drain, 2),
        "wealth_pressure": round(wealth_pressure, 2),
        "officer_pressure": round(officer_pressure, 2),
        "draining_pressure": round(output_drain + wealth_pressure, 2),
        "controlling_pressure": round(officer_pressure, 2),
        "supporting_elements": [resource_element, same_element],
        "draining_elements": [output_element, wealth_element, officer_element],
        "key_reasons": key_reasons,
    }


def _resource_element(day_element: str) -> str:
    return next(element for element, generated in GENERATES.items() if generated == day_element)


def _wealth_element(day_element: str) -> str:
    wealth_map = {
        "wood": "earth",
        "fire": "metal",
        "earth": "water",
        "metal": "wood",
        "water": "fire",
    }
    return wealth_map[day_element]


def _officer_element(day_element: str) -> str:
    officer_map = {
        "wood": "metal",
        "fire": "water",
        "earth": "wood",
        "metal": "fire",
        "water": "earth",
    }
    return officer_map[day_element]


def _strength_label(score: int) -> tuple[str, str]:
    if score >= 68:
        return "strong", "신강"
    if score >= 58:
        return "slightly_strong", "약간 신강"
    if score >= 43:
        return "balanced", "균형"
    if score >= 33:
        return "slightly_weak", "약간 신약"
    return "weak", "신약"


def _build_reason_lines(
    *,
    day_element: str,
    resource_element: str,
    output_element: str,
    wealth_element: str,
    officer_element: str,
    weighted_scores: dict,
    season_factor: dict,
    same_support: float,
    resource_support: float,
    output_drain: float,
    wealth_pressure: float,
    officer_pressure: float,
) -> list[str]:
    reasons: list[str] = []
    season_strength = season_factor[day_element]
    if season_strength >= 1.12:
        reasons.append(f"계절 흐름이 {ELEMENT_LABELS[day_element]} 일간을 비교적 강하게 받쳐 주는 편입니다.")
    elif season_strength <= 0.9:
        reasons.append(f"계절 흐름상 {ELEMENT_LABELS[day_element]} 일간은 힘을 온전히 쓰기 어려운 편입니다.")

    if same_support + resource_support >= output_drain + wealth_pressure + officer_pressure:
        reasons.append(
            f"{ELEMENT_LABELS[resource_element]}와 {ELEMENT_LABELS[day_element]} 쪽 도움이 커서 중심 기운이 쉽게 꺼지지 않는 편입니다."
        )
    else:
        reasons.append(
            f"{ELEMENT_LABELS[output_element]}, {ELEMENT_LABELS[wealth_element]}, {ELEMENT_LABELS[officer_element]} 쪽 부담이 겹쳐 중심 기운이 쉽게 소모될 수 있습니다."
        )

    top_element = max(weighted_scores, key=weighted_scores.get)
    reasons.append(
        f"현재 가중치 기준으로는 {ELEMENT_LABELS[top_element]} 기운이 가장 크게 읽혀 전체 균형 판단에 직접 영향을 줍니다."
    )
    return reasons
