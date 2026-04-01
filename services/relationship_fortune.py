"""Relationship and marriage fortune interpretation."""

from __future__ import annotations

from services.interpretation_engine import build_relationship_section

RELATIONSHIP_RULES = {
    "wealth": {
        "trend": "인연 유입",
        "strong": "인연운이 강하게 들어오지만 속도보다 안정성을 먼저 확인해야 하는 흐름입니다.",
        "medium": "사람 흐름이 열리되 감정과 현실 조건을 함께 보는 편이 좋은 흐름입니다.",
        "light": "관계의 문이 조금씩 열리므로 자연스러운 접점을 넓히는 편이 좋습니다.",
        "strengths": [
            "새로운 만남이나 관계로 이어질 외부 접점이 늘어날 수 있습니다.",
            "호감이 생기더라도 현실 조건을 같이 보는 태도가 오히려 관계를 안정시킵니다.",
        ],
        "warnings": [
            "감정이 앞서면 속도가 빨라질 수 있어 결정은 한 박자 늦추는 편이 좋습니다.",
        ],
    },
    "officer": {
        "trend": "안정/판단",
        "strong": "관계의 방향이 또렷해지지만 기준을 분명히 세워야 흐름이 살아나는 시기입니다.",
        "medium": "인연보다 관계의 안정성과 책임감이 더 중요해지는 흐름입니다.",
        "light": "천천히 관계의 기준을 정리하면 흐름이 부드럽게 이어질 수 있습니다.",
        "strengths": [
            "책임감 있는 인연이나 관계 정리가 눈에 들어오기 쉬운 시기입니다.",
            "관계의 기준을 분명히 할수록 안정성이 높아집니다.",
        ],
        "warnings": [
            "상대의 속도보다 자신의 판단 기준을 먼저 확인하는 편이 좋습니다.",
        ],
    },
    "mixed": {
        "trend": "재정비",
        "strong": "관계는 유지보다 재정비 흐름이 강해 감정의 속도와 거리 조절이 핵심이 됩니다.",
        "medium": "새 인연보다 소통 방식과 거리 조절을 손보는 쪽에 무게가 실립니다.",
        "light": "관계 흐름은 서서히 움직이므로 대화의 톤을 정리하는 편이 좋습니다.",
        "strengths": [
            "대화 방식과 거리 조절을 정리하면 관계 흐름이 한결 부드러워질 수 있습니다.",
        ],
        "warnings": [
            "감정 기복이 큰 날에는 결론을 서두르지 않는 편이 안전합니다.",
        ],
    },
}


def build_relationship_fortune(gender: str, year_fortune: dict) -> dict:
    """Build a relationship fortune from gender-specific stars and yearly flow."""
    current_stars = [year_fortune["ten_god"], year_fortune["daewoon_ten_god"]]
    current_star_set = set(current_stars)

    if gender == "male":
        relevant_stars = {"편재", "정재"}
        profile = "wealth"
    elif gender == "female":
        relevant_stars = {"편관", "정관"}
        profile = "officer"
    else:
        relevant_stars = {"편재", "정재", "편관", "정관"}
        profile = "mixed"

    strength_profile = profile if current_star_set & relevant_stars else "mixed"
    intensity = _resolve_intensity(current_stars, strength_profile)
    rule = RELATIONSHIP_RULES[strength_profile]
    strengths = list(rule["strengths"])
    warnings = list(rule["warnings"])

    if "겁재" in current_star_set or "상관" in current_star_set:
        warnings.append("관계에서는 말의 강약이 강해질 수 있어 서두른 확정은 피하는 편이 좋습니다.")
    if "정인" in current_star_set or "편인" in current_star_set:
        strengths.append("상대를 천천히 이해하려는 태도가 관계 안정에 도움이 됩니다.")
    explanation = _build_explanation(strength_profile, current_stars)
    advice = _build_advice(strength_profile, current_star_set)
    headline = _build_headline(strength_profile, intensity)
    section = build_relationship_section(
        headline=headline,
        explanation=explanation,
        advice=advice,
        strengths=strengths[:2],
        warnings=warnings[:2],
        seed=len("".join(current_stars)) + len(strength_profile),
    )

    return {
        "headline": section["one_line"],
        "summary": rule[intensity],
        "explanation": " ".join(section["easy_explanation"]),
        "advice": " ".join(section["action_advice"]),
        "section": section,
        "trend": rule["trend"],
        "intensity": intensity,
        "intensity_kor": {"strong": "강", "medium": "보통", "light": "완만"}[intensity],
        "strengths": strengths[:2],
        "warnings": warnings[:2],
    }


def _resolve_intensity(stars: list[str], profile: str) -> str:
    if profile != "mixed" and stars[0] == stars[1]:
        return "strong"
    if any(star in {"겁재", "상관", "편재", "편관"} for star in stars):
        return "medium"
    return "light"


def _build_headline(profile: str, intensity: str) -> str:
    headline_map = {
        ("wealth", "strong"): "인연 유입은 강하지만 관계 속도 조절이 더 중요합니다.",
        ("wealth", "medium"): "새로운 만남 가능성은 있지만 서두르지 않는 편이 좋습니다.",
        ("wealth", "light"): "가벼운 접점을 넓히며 흐름을 지켜보기 좋은 시기입니다.",
        ("officer", "strong"): "관계 판단이 또렷해져 기준을 분명히 해야 하는 시기입니다.",
        ("officer", "medium"): "인연보다 관계의 안정성과 책임감을 먼저 볼 시기입니다.",
        ("officer", "light"): "천천히 관계 기준을 맞춰 가기 좋은 흐름입니다.",
        ("mixed", "strong"): "관계는 유지보다 재정비 흐름이 더 강하게 들어옵니다.",
        ("mixed", "medium"): "관계 속도보다 대화 방식 조정이 먼저입니다.",
        ("mixed", "light"): "감정의 결론을 서두르지 않으면 흐름이 부드럽습니다.",
    }
    return headline_map[(profile, intensity)]


def _build_explanation(profile: str, stars: list[str]) -> str:
    year_star, daewoon_star = stars
    profile_phrase = {
        "wealth": "사람과 감정 흐름이 바깥에서 들어오며 관계 속도가 빨라질 수 있습니다.",
        "officer": "관계의 기준과 책임감이 부각되어 감정보다 안정성이 먼저 보일 수 있습니다.",
        "mixed": "새 인연보다 현재 관계를 어떻게 조정할지가 더 중요하게 느껴질 수 있습니다.",
    }[profile]
    return (
        f"세운에서는 {year_star}, 대운에서는 {daewoon_star} 흐름이 겹칩니다. "
        f"{profile_phrase}"
    )


def _build_advice(profile: str, star_set: set[str]) -> str:
    if "겁재" in star_set or "상관" in star_set:
        return "호감이 생겨도 속도를 늦추고 말의 강약을 조절하는 편이 좋습니다."
    if profile == "wealth":
        return "인연이 보여도 감정만 보지 말고 생활 리듬과 현실 조건을 같이 보는 편이 좋습니다."
    if profile == "officer":
        return "상대 기준보다 내 기준을 먼저 분명히 해야 관계가 안정됩니다."
    return "관계를 바로 정의하기보다 대화 방식과 거리 조절부터 정리하는 편이 좋습니다."
