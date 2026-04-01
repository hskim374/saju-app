"""Top summary card builder for result pages."""

from __future__ import annotations


def build_summary_card(
    element_analysis: dict,
    year_fortune: dict,
    career_fortune: dict,
    relationship_fortune: dict,
) -> dict:
    """Build a short at-a-glance summary card."""
    dominant = element_analysis["dominant"]
    if "earth" in dominant:
        wealth = "벌기보다 쌓는 전략"
    elif "metal" in dominant:
        wealth = "기준을 세워 지키는 전략"
    elif "fire" in dominant:
        wealth = "기회 포착 후 지출 통제"
    elif "water" in dominant:
        wealth = "흐름을 읽고 유동적으로 운영"
    else:
        wealth = "확장보다 방향 설정 우선"

    year_trend = _build_year_trend(year_fortune["focus"])
    career = _build_career_card(career_fortune["trend"])
    relationship = _build_relationship_card(relationship_fortune["trend"])

    return {
        "year_trend": year_trend,
        "wealth": wealth,
        "career": career,
        "relationship": relationship,
    }


def _build_year_trend(focus: list[str]) -> str:
    focus_set = set(focus)
    if {"기회", "재물"} <= focus_set:
        return "기회 활용 + 재물 관리 병행"
    if {"안정", "축적"} & focus_set:
        return "안정 유지 + 실속 관리"
    if {"직장", "책임", "평가"} & focus_set:
        return "책임 확대 + 평가 대응"
    if {"변화", "표현", "조율"} & focus_set:
        return "변화 대응 + 표현 조절"
    if {"학습", "지원", "안정"} & focus_set:
        return "기반 정비 + 다음 단계 준비"
    return "흐름 파악 + 우선순위 조정"


def _build_career_card(trend: str) -> str:
    mapping = {
        "평가/책임": "책임 확대, 평판 관리 중요",
        "성과/관리": "성과와 관리 병행",
        "표현/실행": "실행력과 조율이 핵심",
        "유지/정비": "유지와 정비가 우선",
    }
    return mapping.get(trend, trend)


def _build_relationship_card(trend: str) -> str:
    mapping = {
        "인연 유입": "인연 유입, 속도 조절 필요",
        "안정/판단": "관계 판단, 안정성 우선",
        "재정비": "관계 재정비, 대화 조정 필요",
    }
    return mapping.get(trend, trend)
