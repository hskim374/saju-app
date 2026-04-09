"""Simple yongshin/heeshin candidate analysis."""

from __future__ import annotations

ELEMENT_LABELS = {
    "wood": "목(木)",
    "fire": "화(火)",
    "earth": "토(土)",
    "metal": "금(金)",
    "water": "수(水)",
}

CONFIDENCE_LABELS = {
    "high": "높음",
    "medium": "중간",
    "low": "낮음",
}


def calculate_yongshin_candidates(
    saju: dict,
    element_analysis: dict,
    strength_analysis: dict,
) -> dict:
    """Return balanced yongshin/heesin candidates with plain-language reasons."""
    weighted_scores = element_analysis["weighted_scores"]
    label = strength_analysis["label"]

    if label in {"weak", "slightly_weak"}:
        candidate_pool = [
            strength_analysis["resource_element"],
            strength_analysis["same_element"],
        ]
        direction = "보강"
    elif label in {"strong", "slightly_strong"}:
        candidate_pool = [
            strength_analysis["output_element"],
            strength_analysis["wealth_element"],
            strength_analysis["officer_element"],
        ]
        direction = "설기·조절"
    else:
        weakest = sorted(weighted_scores, key=weighted_scores.get)
        candidate_pool = weakest[:3]
        direction = "균형 조정"

    ranked_candidates = sorted(candidate_pool, key=lambda element: (weighted_scores[element], element))
    primary = ranked_candidates[0]
    secondary = ranked_candidates[1] if len(ranked_candidates) > 1 else ranked_candidates[0]
    gap = abs(weighted_scores[secondary] - weighted_scores[primary]) if secondary != primary else 1.0
    confidence = "high" if gap >= 0.8 else "medium" if gap >= 0.3 else "low"

    reasons = _build_reason_lines(
        strength_label=strength_analysis["display_label"],
        direction=direction,
        primary=primary,
        secondary=secondary,
        weighted_scores=weighted_scores,
    )
    cautions = _build_cautions(label=label, strength_analysis=strength_analysis)

    return {
        "primary_candidate": primary,
        "secondary_candidate": secondary,
        "display": {
            "primary": ELEMENT_LABELS[primary],
            "secondary": ELEMENT_LABELS[secondary],
        },
        "direction": direction,
        "confidence": confidence,
        "confidence_display": CONFIDENCE_LABELS[confidence],
        "reasons": reasons,
        "cautions": cautions,
    }


def _build_reason_lines(
    *,
    strength_label: str,
    direction: str,
    primary: str,
    secondary: str,
    weighted_scores: dict,
) -> list[str]:
    reasons = [
        f"현재 판정은 {strength_label} 쪽이라 {direction} 관점에서 후보를 잡는 편이 더 자연스럽습니다.",
        f"{ELEMENT_LABELS[primary]} 기운은 현재 가중치가 비교적 낮아 균형을 맞추는 첫 후보로 보기 좋습니다.",
    ]
    if secondary != primary:
        reasons.append(
            f"{ELEMENT_LABELS[secondary]} 기운도 함께 보완하거나 같이 움직일 때 균형 회복 폭이 커질 수 있습니다."
        )
    strongest = max(weighted_scores, key=weighted_scores.get)
    reasons.append(f"반대로 {ELEMENT_LABELS[strongest]} 쪽이 이미 강하게 읽혀 조절 축이 함께 필요합니다.")
    return reasons


def _build_cautions(*, label: str, strength_analysis: dict) -> list[str]:
    if label in {"weak", "slightly_weak"}:
        return [
            f"{ELEMENT_LABELS[strength_analysis['wealth_element']]}나 {ELEMENT_LABELS[strength_analysis['officer_element']]} 부담이 먼저 커지면 피로가 빠르게 올라올 수 있습니다.",
        ]
    if label in {"strong", "slightly_strong"}:
        return [
            f"{ELEMENT_LABELS[strength_analysis['same_element']]}과 {ELEMENT_LABELS[strength_analysis['resource_element']]} 쪽이 더 과해지면 한쪽으로 쏠린 반응이 강해질 수 있습니다.",
        ]
    return [
        "균형형 원국은 특정 기운 하나만 밀기보다 상황에 따라 조절 방향을 같이 보는 편이 더 안전합니다.",
    ]
