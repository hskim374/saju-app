"""Daewoon (10-year fortune cycle) calculations."""

from __future__ import annotations

from datetime import datetime
import math

from data.branches import BRANCHES, BRANCHES_BY_KOR
from data.stems import STEMS, STEMS_BY_KOR
from services.interpretation_engine import build_active_daewoon_section
from services.saju_calculator import (
    build_korean_datetime,
    get_major_solar_term_points,
)
from services.ten_gods import calculate_ten_god_for_stem

DEFAULT_DAEWOON_CYCLE_COUNT = 8

GANZHI_CYCLE = [
    {
        "kor": f"{STEMS[index % 10]['kor']}{BRANCHES[index % 12]['kor']}",
        "hanja": f"{STEMS[index % 10]['hanja']}{BRANCHES[index % 12]['hanja']}",
        "stem": STEMS[index % 10]["kor"],
        "branch": BRANCHES[index % 12]["kor"],
    }
    for index in range(60)
]
GANZHI_INDEX_BY_KOR = {pillar["kor"]: index for index, pillar in enumerate(GANZHI_CYCLE)}

DAEWOON_TEN_GOD_RULES = {
    "비견": {
        "headline": "자기 기준이 강해져 방향을 직접 잡으려는 흐름이 커집니다.",
        "summary": "자기 기준이 강해져 방향을 직접 잡으려는 흐름이 커집니다.",
        "explanation": "내가 정한 기준으로 움직이려는 힘이 강해져 독립성과 주도권이 부각되기 쉽습니다.",
        "advice": "고집으로 흐르지 않도록 협업 기준과 역할 선을 먼저 정해 두는 편이 좋습니다.",
        "keywords": ["자기주도", "역할확장", "독립성"],
    },
    "겁재": {
        "headline": "경쟁과 분산이 함께 들어와 선택과 관계 조율이 중요해집니다.",
        "summary": "경쟁과 분산이 함께 들어와 선택과 관계 조율이 중요해집니다.",
        "explanation": "사람과 기회가 동시에 늘 수 있지만 자원과 감정이 여러 방향으로 흩어질 가능성도 커집니다.",
        "advice": "모든 기회를 잡기보다 우선순위를 먼저 정하고 관계 경계를 분명히 하는 편이 좋습니다.",
        "keywords": ["경쟁", "분산관리", "대인조율"],
    },
    "식신": {
        "headline": "실무 성과를 꾸준히 쌓아 생활 기반을 넓히기 좋은 흐름입니다.",
        "summary": "실무 성과를 꾸준히 쌓아 생활 기반을 넓히기 좋은 흐름입니다.",
        "explanation": "손에 잡히는 결과를 차곡차곡 만드는 힘이 살아나 생활 기반을 넓히기 쉬운 시기입니다.",
        "advice": "실행 기록과 결과 정리를 함께 남기면 이 시기의 성과가 더 오래 갑니다.",
        "keywords": ["성과", "생산성", "안정성"],
    },
    "상관": {
        "headline": "표현과 변화 욕구가 강해져 방식 전환이 잦아질 수 있는 흐름입니다.",
        "summary": "표현과 변화 욕구가 강해져 방식 전환이 잦아질 수 있는 흐름입니다.",
        "explanation": "답답한 틀을 깨고 싶은 마음이 커져 표현력은 살아나지만 마찰도 함께 커질 수 있습니다.",
        "advice": "바꿀 것과 지킬 것을 먼저 나눠 두면 변화가 성과로 이어지기 쉽습니다.",
        "keywords": ["표현", "변화", "조율"],
    },
    "편재": {
        "headline": "기회와 외부 활동이 늘어 판이 넓어지기 쉬운 흐름입니다.",
        "summary": "기회와 외부 활동이 늘어 판이 넓어지기 쉬운 흐름입니다.",
        "explanation": "밖에서 들어오는 제안과 사람 흐름이 늘어 활동 반경이 커질 가능성이 높습니다.",
        "advice": "선택 기준 없이 움직이면 분산되기 쉬우니 잡을 기회와 놓을 기회를 먼저 구분하는 편이 좋습니다.",
        "keywords": ["확장", "기회", "대외활동"],
    },
    "정재": {
        "headline": "생활 재무와 현실 관리가 안정적으로 쌓이는 흐름입니다.",
        "summary": "생활 재무와 현실 관리가 안정적으로 쌓이는 흐름입니다.",
        "explanation": "생활 운영과 재무 기준을 정리할수록 성과가 눈에 보이게 쌓이는 시기입니다.",
        "advice": "고정비, 저축, 일상 관리 기준을 숫자로 정리해 두면 장점이 더 크게 살아납니다.",
        "keywords": ["축적", "관리", "현실감"],
    },
    "편관": {
        "headline": "압박과 책임이 강해지지만 버티면 자리 변화를 만들 수 있는 흐름입니다.",
        "summary": "압박과 책임이 강해지지만 버티면 자리 변화를 만들 수 있는 흐름입니다.",
        "explanation": "긴장과 책임이 함께 늘어 체감은 무겁지만, 그만큼 자리 변화를 만들 동력도 커집니다.",
        "advice": "버티는 힘만 믿기보다 체력과 일정의 상한선을 정해 두는 편이 좋습니다.",
        "keywords": ["압박", "도전", "규율"],
    },
    "정관": {
        "headline": "조직과 책임의 무게가 커지며 평가 기준이 또렷해지는 흐름입니다.",
        "summary": "조직과 책임의 무게가 커지며 평가 기준이 또렷해지는 흐름입니다.",
        "explanation": "역할과 책임이 분명해지고 공적인 평가를 받을 일이 늘어날 수 있는 시기입니다.",
        "advice": "기준과 원칙을 먼저 세우면 부담이 오히려 신뢰로 바뀌기 쉽습니다.",
        "keywords": ["책임", "직장", "평가"],
    },
    "편인": {
        "headline": "익숙한 방식에서 벗어나 시야를 바꾸게 되는 흐름이 강해집니다.",
        "summary": "익숙한 방식에서 벗어나 시야를 바꾸게 되는 흐름이 강해집니다.",
        "explanation": "기존 방식이 답답하게 느껴져 다른 길, 다른 시각, 다른 공부를 찾게 되는 흐름입니다.",
        "advice": "모든 선택지를 한꺼번에 벌리기보다 실험할 영역을 좁혀 두는 편이 좋습니다.",
        "keywords": ["전환", "탐색", "관점변화"],
    },
    "정인": {
        "headline": "배움과 지원 기반이 단단해져 다음 단계를 준비하기 좋은 흐름입니다.",
        "summary": "배움과 지원 기반이 단단해져 다음 단계를 준비하기 좋은 흐름입니다.",
        "explanation": "준비, 공부, 지원 기반을 다질수록 다음 흐름이 부드럽게 연결되는 시기입니다.",
        "advice": "지금은 서두른 확장보다 준비와 자격, 자료 축적에 시간을 쓰는 편이 유리합니다.",
        "keywords": ["학습", "지원", "정비"],
    },
}

DAEWOON_ELEMENT_TAILS = {
    "wood": [
        "목 기운이 받쳐 확장과 방향 전환이 자연스럽게 붙습니다.",
        "목 기운이 실려 사람과 계획을 넓히는 움직임이 살아납니다.",
    ],
    "fire": [
        "화 기운이 더해져 실행 속도와 표현 강도가 함께 올라갑니다.",
        "화 기운이 겹쳐 바깥 활동과 존재감이 커지기 쉽습니다.",
    ],
    "earth": [
        "토 기운이 받쳐 생활 기반과 현실 감각을 다지기 좋습니다.",
        "토 기운이 실려 유지력과 버티는 힘이 안정적으로 붙습니다.",
    ],
    "metal": [
        "금 기운이 겹쳐 기준 정리와 마감 능력이 더 또렷해집니다.",
        "금 기운이 실려 판단과 구조화의 힘이 강해집니다.",
    ],
    "water": [
        "수 기운이 더해져 흐름 파악과 유연한 대응이 중요해집니다.",
        "수 기운이 실려 정보 수집과 타이밍 조절 능력이 살아납니다.",
    ],
}


def calculate_daewoon(
    saju_result: dict,
    gender: str = "unknown",
    cycle_count: int = DEFAULT_DAEWOON_CYCLE_COUNT,
) -> dict:
    """Calculate the 10-year fortune cycles from the natal chart."""
    if gender not in {"male", "female", "unknown"}:
        raise ValueError("성별은 male, female, unknown 중 하나여야 합니다.")

    raw_input = saju_result["raw_input"]
    resolved_solar = saju_result["resolved_solar"]
    birth_moment = _build_birth_moment_from_result(raw_input, resolved_solar)
    year_stem = saju_result["saju"]["year"]["stem"]
    month_pillar = saju_result["saju"]["month"]

    direction = _resolve_direction(year_stem, gender)
    boundary = _find_reference_term(birth_moment, direction)
    diff_days = abs((boundary.at - birth_moment).total_seconds()) / 86400
    start_age_float = round(diff_days / 3, 2)
    start_age = max(1, math.ceil(diff_days / 3))
    cycles = _build_cycles(
        month_pillar=month_pillar,
        start_age=start_age,
        direction=direction,
        birth_year=resolved_solar["year"],
        cycle_count=cycle_count,
        day_stem=saju_result["saju"]["day"]["stem"],
    )
    current_age = max(1, date_today_year() - resolved_solar["year"] + 1)
    active_cycle = get_active_daewoon_cycle({"cycles": cycles}, current_age)
    active_section = build_active_daewoon_section(
        headline=active_cycle["headline"],
        explanation=active_cycle["explanation"],
        advice=active_cycle["advice"],
        keywords=active_cycle["keywords"],
        seed=current_age + start_age,
    )

    return {
        "direction": direction,
        "direction_kor": "순행" if direction == "forward" else "역행",
        "gender_basis": gender,
        "start_age": start_age,
        "start_age_display": _build_start_age_display(start_age),
        "start_age_float": start_age_float,
        "start_term": boundary.name,
        "start_term_at": boundary.at.isoformat(),
        "days_to_start_term": round(diff_days, 2),
        "cycles": cycles,
        "active_cycle_summary": {
            "nominal_age": current_age,
            "pillar": active_cycle["pillar"],
            "stem": active_cycle["stem"],
            "branch": active_cycle["branch"],
            "ten_god": active_cycle["ten_god"],
            "headline": active_section["one_line"],
            "summary": active_cycle["summary"],
            "explanation": " ".join(active_section["easy_explanation"]),
            "real_life": active_section["real_life"],
            "advice": " ".join(active_section["action_advice"]),
            "section": active_section,
            "keywords": active_cycle["keywords"],
        },
        "basis": {
            "direction_rule": "양년 남성/음년 여성 순행, 음년 남성/양년 여성 역행, 미입력은 남성 규칙 적용",
            "start_age_rule": "출생시각부터 순행은 다음 절입, 역행은 이전 절입까지의 차이를 3으로 나눈 뒤 올림",
        },
    }


def get_active_daewoon_cycle(daewoon: dict, nominal_age: int) -> dict:
    """Return the active daewoon cycle for the provided nominal age."""
    for cycle in daewoon["cycles"]:
        if cycle["start_age"] <= nominal_age <= cycle["end_age"]:
            return cycle
    return daewoon["cycles"][-1]


def _build_birth_moment_from_result(raw_input: dict, resolved_solar: dict) -> datetime:
    hour = raw_input["hour"] if raw_input["hour"] is not None else 12
    minute = raw_input["minute"] if raw_input["minute"] is not None else 0
    return build_korean_datetime(
        resolved_solar["year"],
        resolved_solar["month"],
        resolved_solar["day"],
        hour,
        minute,
    )


def _resolve_direction(year_stem_kor: str, gender: str) -> str:
    stem = STEMS_BY_KOR[year_stem_kor]
    effective_gender = "male" if gender == "unknown" else gender
    is_yang_year = stem["yin_yang"] == "yang"
    if (effective_gender == "male" and is_yang_year) or (
        effective_gender == "female" and not is_yang_year
    ):
        return "forward"
    return "reverse"


def _find_reference_term(birth_moment: datetime, direction: str):
    points = (
        list(get_major_solar_term_points(birth_moment.year - 1))
        + list(get_major_solar_term_points(birth_moment.year))
        + list(get_major_solar_term_points(birth_moment.year + 1))
    )
    if direction == "forward":
        return next(point for point in points if point.at > birth_moment)
    return next(point for point in reversed(points) if point.at < birth_moment)


def _build_cycles(
    month_pillar: dict,
    start_age: int,
    direction: str,
    birth_year: int,
    cycle_count: int,
    day_stem: str,
) -> list[dict]:
    month_index = GANZHI_INDEX_BY_KOR[month_pillar["kor"]]
    step = 1 if direction == "forward" else -1
    cycles = []
    for cycle_number in range(cycle_count):
        pillar_index = (month_index + step * (cycle_number + 1)) % 60
        start_cycle_age = start_age + cycle_number * 10
        end_cycle_age = start_cycle_age + 9
        pillar = GANZHI_CYCLE[pillar_index]
        ten_god = calculate_ten_god_for_stem(day_stem, pillar["stem"])
        branch_element = BRANCHES_BY_KOR[pillar["branch"]]["element"]
        interpretation = _build_cycle_interpretation(ten_god, branch_element, cycle_number)
        cycles.append(
            {
                "start_age": start_cycle_age,
                "end_age": end_cycle_age,
                "start_year": birth_year + start_cycle_age,
                "end_year": birth_year + end_cycle_age,
                "pillar": pillar["kor"],
                "hanja": pillar["hanja"],
                "stem": pillar["stem"],
                "branch": pillar["branch"],
                "ten_god": ten_god,
                "headline": interpretation["headline"],
                "summary": interpretation["summary"],
                "explanation": interpretation["explanation"],
                "advice": interpretation["advice"],
                "keywords": interpretation["keywords"],
            }
        )
    return cycles


def _build_cycle_interpretation(ten_god: str, branch_element: str, cycle_number: int) -> dict:
    base = DAEWOON_TEN_GOD_RULES[ten_god]
    tail_options = DAEWOON_ELEMENT_TAILS[branch_element]
    tail = tail_options[cycle_number % len(tail_options)]
    return {
        "headline": base["headline"],
        "summary": f"{base['summary']} {tail}",
        "explanation": f"{base['explanation']} {tail}",
        "advice": base["advice"],
        "keywords": base["keywords"],
    }


def _build_start_age_display(start_age: int) -> str:
    if start_age <= 1:
        return "출생 직후 (약 1세 전후)"
    if start_age <= 3:
        return f"이른 시기 (약 {start_age}세 전후)"
    if start_age <= 6:
        return f"유년기 무렵 (약 {start_age}세 전후)"
    return f"아동기 이후 (약 {start_age}세 전후)"


def date_today_year() -> int:
    return datetime.now().year
