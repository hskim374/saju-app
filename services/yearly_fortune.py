"""Yearly fortune calculation based on natal chart and daewoon."""

from __future__ import annotations

from services.interpretation_engine import build_yearly_section
from services.daewoon import get_active_daewoon_cycle
from services.saju_calculator import build_korean_datetime, get_year_month_pillars_for_datetime
from services.ten_gods import calculate_ten_god_for_stem

YEARLY_TEN_GOD_RULES = {
    "비견": {
        "headline": "주도권과 역할 조정이 중요한 해입니다.",
        "summary": "주도권과 역할 조정이 중요한 해입니다.",
        "explanation": "내 판단과 역할이 앞에 서기 쉬워 스스로 정한 기준이 실제 결과에 직접 연결되기 쉽습니다.",
        "advice": "내 주장만 세우기보다 협업 기준을 먼저 정하는 편이 좋습니다.",
        "focus": ["자기주도", "협업", "역할조정"],
    },
    "겁재": {
        "headline": "경쟁과 분산을 조절해야 하는 해입니다.",
        "summary": "경쟁과 분산을 조절해야 하는 해입니다.",
        "explanation": "사람과 기회가 동시에 늘 수 있지만 자원과 에너지도 쉽게 분산될 수 있는 해입니다.",
        "advice": "우선순위를 줄이고 지출과 관계 경계를 함께 관리하는 편이 좋습니다.",
        "focus": ["경쟁", "지출관리", "대인관계"],
    },
    "식신": {
        "headline": "실행력과 생산성을 끌어올리기 좋은 해입니다.",
        "summary": "실행력과 생산성을 끌어올리기 좋은 해입니다.",
        "explanation": "한 번 움직인 일이 실제 결과로 쌓이기 쉬워 생활 성과를 남기기 좋은 흐름입니다.",
        "advice": "기록과 결과 정리를 함께 하면 한 해의 성과가 더 또렷하게 남습니다.",
        "focus": ["성과", "실행", "생산성"],
    },
    "상관": {
        "headline": "표현과 변화가 강해지는 해입니다.",
        "summary": "표현과 변화가 강해지는 해입니다.",
        "explanation": "말과 방식의 힘이 강해져 변화 욕구가 커지지만 마찰도 함께 커질 수 있습니다.",
        "advice": "강한 표현은 한 번 정리해서 내보내는 편이 좋습니다.",
        "focus": ["변화", "표현", "조율"],
    },
    "편재": {
        "headline": "기회 포착과 대외 활동이 늘어나는 해입니다.",
        "summary": "기회 포착과 대외 활동이 늘어나는 해입니다.",
        "explanation": "밖에서 들어오는 제안과 접점이 늘어 활동 반경이 넓어지기 쉬운 해입니다.",
        "advice": "기회를 고르지 않으면 성과가 흩어지기 쉬우니 선별 기준이 필요합니다.",
        "focus": ["기회", "재물", "대외활동"],
    },
    "정재": {
        "headline": "안정적인 관리와 축적이 중요한 해입니다.",
        "summary": "안정적인 관리와 축적이 중요한 해입니다.",
        "explanation": "관리와 실무, 생활 기준을 정리할수록 실속이 쌓이기 쉬운 해입니다.",
        "advice": "예산과 시간표를 수치로 관리하면 장점이 더 크게 살아납니다.",
        "focus": ["안정", "축적", "실무"],
    },
    "편관": {
        "headline": "압박과 도전을 관리해야 하는 해입니다.",
        "summary": "압박과 도전을 관리해야 하는 해입니다.",
        "explanation": "긴장과 책임이 동시에 늘 수 있어 체감은 무겁지만 성장 압력도 커지는 해입니다.",
        "advice": "체력과 일정 상한선을 정해 두고 무리한 승부는 늦추는 편이 좋습니다.",
        "focus": ["도전", "규율", "긴장관리"],
    },
    "정관": {
        "headline": "책임과 평가가 부각되는 해입니다.",
        "summary": "책임과 평가가 부각되는 해입니다.",
        "explanation": "조직과 책임의 무게가 커져 평판과 역할이 더 또렷하게 보이기 쉬운 해입니다.",
        "advice": "기준과 원칙을 먼저 세우면 부담이 신뢰로 바뀌기 쉽습니다.",
        "focus": ["직장", "책임", "평가"],
    },
    "편인": {
        "headline": "전환과 직관이 함께 작동하는 해입니다.",
        "summary": "전환과 직관이 함께 작동하는 해입니다.",
        "explanation": "기존 방식이 답답해져 다른 시각과 새로운 선택지를 찾게 되는 해입니다.",
        "advice": "실험 범위를 좁혀 두면 전환이 더 안정적으로 이어집니다.",
        "focus": ["전환", "직관", "탐색"],
    },
    "정인": {
        "headline": "배움과 지원 기반을 다지기 좋은 해입니다.",
        "summary": "배움과 지원 기반을 다지기 좋은 해입니다.",
        "explanation": "준비와 배움, 자료 축적이 실제 안정감으로 이어지기 쉬운 해입니다.",
        "advice": "확장보다 준비와 자격, 자료 정리에 시간을 쓰는 편이 좋습니다.",
        "focus": ["학습", "지원", "안정"],
    },
}


def calculate_yearly_fortune(
    saju_result: dict,
    daewoon: dict,
    target_year: int,
) -> dict:
    """Build a yearly fortune summary from the target year's annual pillar."""
    reference_moment = build_korean_datetime(target_year, 7, 1, 12, 0)
    year_pillar = get_year_month_pillars_for_datetime(reference_moment)["year"]
    day_stem = saju_result["saju"]["day"]["stem"]
    year_ten_god = calculate_ten_god_for_stem(day_stem, year_pillar["stem"])
    nominal_age = max(1, target_year - saju_result["resolved_solar"]["year"] + 1)
    active_cycle = get_active_daewoon_cycle(daewoon, nominal_age)
    daewoon_ten_god = calculate_ten_god_for_stem(day_stem, active_cycle["stem"])
    year_rule = YEARLY_TEN_GOD_RULES[year_ten_god]
    daewoon_rule = YEARLY_TEN_GOD_RULES[daewoon_ten_god]

    focus = _dedupe(year_rule["focus"] + daewoon_rule["focus"])[:3]
    summary = f"{year_rule['summary']} 대운에서는 {daewoon_rule['focus'][0]} 흐름이 겹칩니다."
    explanation = (
        f"{year_rule['explanation']} "
        f"여기에 현재 대운의 {daewoon_ten_god} 흐름이 겹쳐 {daewoon_rule['focus'][0]} 쪽 체감이 더 커질 수 있습니다."
    )
    advice = (
        f"{year_rule['advice']} "
        f"특히 올해는 {focus[0]}보다 앞서 {focus[1] if len(focus) > 1 else focus[0]}을 정리하는 편이 유리합니다."
    )
    section = build_yearly_section(
        headline=year_rule["headline"],
        explanation=explanation,
        advice=advice,
        focus=focus,
        seed=target_year + nominal_age,
    )

    return {
        "year": target_year,
        "pillar": year_pillar["kor"],
        "hanja": year_pillar["hanja"],
        "stem": year_pillar["stem"],
        "branch": year_pillar["branch"],
        "ten_god": year_ten_god,
        "daewoon_ten_god": daewoon_ten_god,
        "active_age": nominal_age,
        "active_daewoon": {
            "pillar": active_cycle["pillar"],
            "start_age": active_cycle["start_age"],
            "end_age": active_cycle["end_age"],
        },
        "headline": section["one_line"],
        "summary": summary,
        "explanation": " ".join(section["easy_explanation"]),
        "advice": " ".join(section["action_advice"]),
        "section": section,
        "focus": focus,
    }


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
