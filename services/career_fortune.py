"""Career fortune interpretation from natal chart and current flows."""

from __future__ import annotations

from services.interpretation_engine import build_career_section

POSITIVE_STARS = {"정관", "정인", "식신", "정재"}
CHANGE_STARS = {"편관", "편인", "상관", "편재"}
CAUTION_STARS = {"겁재", "상관", "편관"}

CAREER_STRENGTHS = {
    "정관": "조직 안에서 역할이 또렷해지고 책임이 커질 수 있는 흐름입니다.",
    "편관": "압박이 강하지만 버티면 자리 변동이나 역할 확장이 연결될 수 있습니다.",
    "정인": "자격, 학습, 지원 체계를 붙이면 직장운이 안정적으로 받쳐집니다.",
    "편인": "새 방식이나 다른 직무 감각을 익히면 전환 기회를 만들 수 있습니다.",
    "식신": "실무 성과를 꾸준히 쌓아 신뢰를 얻기 좋은 흐름입니다.",
    "상관": "표현력과 문제 제기가 성과로 이어질 수 있지만 강약 조절이 필요합니다.",
    "정재": "관리 능력과 실적을 함께 보여주기 좋은 흐름입니다.",
    "편재": "외부 기회나 자리 이동 가능성이 열릴 수 있는 흐름입니다.",
    "비견": "내 역할을 직접 잡고 주도권을 만드는 데 힘이 실립니다.",
    "겁재": "경쟁이 강해져도 존재감을 드러낼 수 있으나 무리한 승부는 피해야 합니다.",
}

CAREER_WARNINGS = {
    "상관": "평가가 걸린 자리에서는 말의 수위와 문서 표현을 한 번 더 다듬는 편이 좋습니다.",
    "겁재": "올해는 경쟁이 강해져 자리 변동 가능성이 있어 충동적인 이직 판단은 늦추는 편이 안전합니다.",
    "편관": "압박이 커질수록 체력과 감정 소모가 누적될 수 있어 일정 간격으로 리듬을 비워야 합니다.",
    "편재": "기회가 많아 보일수록 우선순위를 정하지 않으면 성과가 흩어질 수 있습니다.",
    "비견": "자기 판단이 강해질수록 협업 신호를 분명히 해야 충돌을 줄일 수 있습니다.",
}


def build_career_fortune(saju_result: dict, year_fortune: dict) -> dict:
    """Build a rule-based career fortune from current yearly flow."""
    current_stars = [year_fortune["ten_god"], year_fortune["daewoon_ten_god"]]
    intensity = _resolve_intensity(current_stars)
    tone = _resolve_tone(current_stars)
    trend = _resolve_trend(current_stars)
    summary = _build_summary(tone, intensity)
    headline = _build_headline(tone, intensity)
    strengths = _pick_messages(current_stars, CAREER_STRENGTHS, limit=2)
    warnings = _pick_messages(current_stars, CAREER_WARNINGS, limit=2)
    if not warnings:
        warnings = ["큰 결정은 일정과 조건을 숫자로 정리한 뒤 판단하는 편이 좋습니다."]
    explanation = _build_explanation(current_stars, trend, tone)
    advice = _build_advice(current_stars, tone)
    section = build_career_section(
        headline=headline,
        explanation=explanation,
        advice=advice,
        strengths=strengths,
        warnings=warnings,
        seed=len("".join(current_stars)) + len(trend),
    )

    return {
        "headline": section["one_line"],
        "summary": summary,
        "explanation": " ".join(section["easy_explanation"]),
        "advice": " ".join(section["action_advice"]),
        "section": section,
        "trend": trend,
        "trend_kor": trend,
        "tone": tone,
        "tone_kor": {"positive": "안정형", "change": "변화형", "caution": "주의형"}[tone],
        "intensity": intensity,
        "intensity_kor": {"strong": "강", "medium": "보통", "light": "완만"}[intensity],
        "strengths": strengths,
        "warnings": warnings,
    }


def _resolve_intensity(stars: list[str]) -> str:
    if stars[0] == stars[1] or sum(star in CHANGE_STARS for star in stars) == 2:
        return "strong"
    if any(star in CHANGE_STARS for star in stars):
        return "medium"
    return "light"


def _resolve_tone(stars: list[str]) -> str:
    if any(star in CAUTION_STARS for star in stars):
        return "caution"
    if any(star in CHANGE_STARS for star in stars):
        return "change"
    return "positive"


def _resolve_trend(stars: list[str]) -> str:
    if "정관" in stars or "편관" in stars:
        return "평가/책임"
    if "편재" in stars or "정재" in stars:
        return "성과/관리"
    if "상관" in stars or "식신" in stars:
        return "표현/실행"
    return "유지/정비"


def _build_summary(tone: str, intensity: str) -> str:
    summary_map = {
        ("positive", "strong"): "올해는 조직 내 역할이 커지고 결과를 보여줄 자리가 선명하게 들어오는 흐름입니다.",
        ("positive", "medium"): "올해는 맡은 역할을 안정적으로 키워 가기 좋은 흐름입니다.",
        ("positive", "light"): "올해는 유지와 관리에 강점을 싣기 좋은 흐름입니다.",
        ("change", "strong"): "올해는 경쟁과 변화가 강해져 자리 이동이나 역할 전환 가능성까지 함께 보이는 흐름입니다.",
        ("change", "medium"): "올해는 변화 대응력이 직장운의 핵심이 되는 흐름입니다.",
        ("change", "light"): "올해는 작은 조정과 방식 전환이 성과에 연결되기 쉬운 흐름입니다.",
        ("caution", "strong"): "올해는 압박과 경쟁이 강해져 자리 변동 가능성까지 염두에 두고 움직여야 하는 흐름입니다.",
        ("caution", "medium"): "올해는 긴장감이 높아질 수 있어 속도보다 관리가 중요한 흐름입니다.",
        ("caution", "light"): "올해는 무리한 확장보다 현재 역할을 단단히 지키는 편이 좋은 흐름입니다.",
    }
    return summary_map[(tone, intensity)]


def _build_headline(tone: str, intensity: str) -> str:
    headline_map = {
        ("positive", "strong"): "성과와 책임이 동시에 커지는 시기입니다.",
        ("positive", "medium"): "성과와 관리 균형이 성과를 좌우합니다.",
        ("positive", "light"): "유지와 관리에 집중할수록 안정감이 커집니다.",
        ("change", "strong"): "기회는 많지만 선택이 성과를 좌우합니다.",
        ("change", "medium"): "변화 대응력이 올해 직장운의 핵심입니다.",
        ("change", "light"): "작은 조정이 일의 흐름을 바꿀 수 있습니다.",
        ("caution", "strong"): "경쟁이 강해져 자리 판단을 신중히 해야 합니다.",
        ("caution", "medium"): "무리한 확장보다 관리가 먼저인 해입니다.",
        ("caution", "light"): "현재 자리의 안정성을 지키는 편이 유리합니다.",
    }
    return headline_map[(tone, intensity)]


def _pick_messages(stars: list[str], source: dict[str, str], limit: int) -> list[str]:
    messages = []
    for star in stars:
        message = source.get(star)
        if message and message not in messages:
            messages.append(message)
        if len(messages) >= limit:
            break
    return messages


def _build_explanation(stars: list[str], trend: str, tone: str) -> str:
    year_star, daewoon_star = stars
    tone_phrase = {
        "positive": "흐름이 비교적 안정적으로 붙어",
        "change": "변화와 조정 이슈가 겹쳐",
        "caution": "긴장과 압박이 함께 올라와",
    }[tone]
    return (
        f"세운에서는 {year_star}, 대운에서는 {daewoon_star} 흐름이 작동합니다. "
        f"{tone_phrase} 직장에서는 {trend} 이슈가 실제 성과와 평판에 바로 연결되기 쉬운 시기입니다."
    )


def _build_advice(stars: list[str], tone: str) -> str:
    if "편재" in stars:
        return "기회가 늘수록 바로 움직이기보다 기준에 맞는 일만 고르는 편이 좋습니다."
    if "겁재" in stars:
        return "경쟁이 강할수록 모든 일을 직접 쥐기보다 선택과 위임을 같이 쓰는 편이 좋습니다."
    if "정관" in stars or "편관" in stars:
        return "책임이 커질수록 속도보다 기준과 일정 관리에 힘을 두는 편이 좋습니다."
    if tone == "positive":
        return "올해는 실적을 조용히 쌓기보다 보이게 정리해 두는 편이 더 유리합니다."
    return "변화가 보여도 바로 갈아타기보다 현재 자리에서 관리 기준을 먼저 세우는 편이 좋습니다."
