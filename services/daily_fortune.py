"""Daily fortune calculation from a target solar date."""

from __future__ import annotations

from datetime import date

from services.interpretation_engine import build_daily_section
from services.saju_calculator import get_day_pillar_for_solar_date
from services.ten_gods import calculate_ten_god_for_stem

DAILY_RULES = {
    "비견": {
        "headline": "주도적으로 움직이되 고집은 줄이는 편이 좋은 날입니다.",
        "summary": "주도적으로 움직이되 고집은 줄이는 편이 좋은 날입니다.",
        "explanation": "내 판단이 앞에 서기 쉬워 빠르게 결정할 수 있지만, 주변 조율을 빼먹기 쉬운 흐름입니다.",
        "advice": "결정을 내리기 전 상대 일정과 조건을 한 번 더 확인하는 편이 좋습니다.",
        "keywords": ["주도", "균형", "협업"],
    },
    "겁재": {
        "headline": "경쟁심이 올라오기 쉬워 지출과 관계를 함께 점검하는 것이 좋습니다.",
        "summary": "경쟁심이 올라오기 쉬워 지출과 관계를 함께 점검하는 것이 좋습니다.",
        "explanation": "사람과 일의 자극이 강해져 감정과 지출이 생각보다 쉽게 커질 수 있습니다.",
        "advice": "승부를 빨리 보려 하지 말고 오늘 쓸 힘과 돈의 한도를 먼저 정해 두는 편이 좋습니다.",
        "keywords": ["주의", "경쟁", "분산"],
    },
    "식신": {
        "headline": "실무와 생산성을 차분히 끌어올리기 좋은 날입니다.",
        "summary": "실무와 생산성을 차분히 끌어올리기 좋은 날입니다.",
        "explanation": "손에 잡히는 결과를 만들기 좋은 날이라 미뤄 둔 일을 정리하기에 적합합니다.",
        "advice": "작은 결과라도 눈에 보이게 마무리하면 하루 흐름이 훨씬 안정됩니다.",
        "keywords": ["성과", "실행", "안정"],
    },
    "상관": {
        "headline": "의사결정은 신중하게 하고 말의 강약을 조절하는 편이 좋습니다.",
        "summary": "의사결정은 신중하게 하고 말의 강약을 조절하는 편이 좋습니다.",
        "explanation": "표현력이 살아나는 대신 강한 말과 빠른 결론이 마찰을 만들 수 있는 날입니다.",
        "advice": "중요한 말과 메시지는 한 번 다듬고 보내는 편이 안전합니다.",
        "keywords": ["주의", "문서", "표현"],
    },
    "편재": {
        "headline": "사람과 기회를 넓히기 좋은 날이지만 선택은 선별적으로 하는 편이 좋습니다.",
        "summary": "사람과 기회를 넓히기 좋은 날이지만 선택은 선별적으로 하는 편이 좋습니다.",
        "explanation": "바깥 제안과 접점이 늘기 쉬워 기회는 보이지만 집중이 흩어질 수 있습니다.",
        "advice": "잡을 일 한두 개만 정하고 나머지는 메모로 넘기는 편이 좋습니다.",
        "keywords": ["기회", "대외활동", "선별"],
    },
    "정재": {
        "headline": "재정과 일정 관리를 정리하기 좋은 날입니다.",
        "summary": "재정과 일정 관리를 정리하기 좋은 날입니다.",
        "explanation": "실무와 생활 기준을 정리할수록 바로 체감되는 안정감이 생기기 쉬운 날입니다.",
        "advice": "결제, 일정, 해야 할 일을 한 번에 정리하면 하루가 훨씬 가벼워집니다.",
        "keywords": ["축적", "관리", "실무"],
    },
    "편관": {
        "headline": "압박이 생겨도 원칙을 유지하면 흐름을 잡기 좋은 날입니다.",
        "summary": "압박이 생겨도 원칙을 유지하면 흐름을 잡기 좋은 날입니다.",
        "explanation": "긴장감이 올라와도 기준을 놓치지 않으면 오히려 정리가 빨라질 수 있습니다.",
        "advice": "무리하게 버티기보다 중요한 일부터 순서대로 줄이는 편이 좋습니다.",
        "keywords": ["긴장", "원칙", "대응"],
    },
    "정관": {
        "headline": "책임감과 신뢰가 드러나기 쉬운 날입니다.",
        "summary": "책임감과 신뢰가 드러나기 쉬운 날입니다.",
        "explanation": "해야 할 일을 분명히 처리할수록 평판과 신뢰가 바로 남기 쉬운 흐름입니다.",
        "advice": "작은 약속이라도 정확히 지키는 편이 오늘 운을 살립니다.",
        "keywords": ["책임", "평가", "신뢰"],
    },
    "편인": {
        "headline": "관점을 바꾸고 정보를 탐색하기 좋은 날입니다.",
        "summary": "관점을 바꾸고 정보를 탐색하기 좋은 날입니다.",
        "explanation": "익숙한 답보다 다른 해석이 더 잘 보일 수 있어 탐색과 비교에 강점이 있습니다.",
        "advice": "새 선택지를 보더라도 바로 옮기기보다 시험해 보는 수준으로 다루는 편이 좋습니다.",
        "keywords": ["탐색", "전환", "통찰"],
    },
    "정인": {
        "headline": "배움과 정리에 집중하면 안정감이 살아나는 날입니다.",
        "summary": "배움과 정리에 집중하면 안정감이 살아나는 날입니다.",
        "explanation": "준비와 정리, 자료 축적이 실제 안정감으로 이어지기 쉬운 하루입니다.",
        "advice": "새 일을 늘리기보다 공부와 정리 시간을 확보하는 편이 좋습니다.",
        "keywords": ["학습", "정리", "안정"],
    },
}


def calculate_daily_fortune(saju_result: dict, target_date: date) -> dict:
    """Return the fortune for a specific solar date."""
    day_pillar = get_day_pillar_for_solar_date(target_date)
    ten_god = calculate_ten_god_for_stem(saju_result["saju"]["day"]["stem"], day_pillar["stem"])
    rule = DAILY_RULES[ten_god]
    section = build_daily_section(
        headline=rule["headline"],
        explanation=rule["explanation"],
        advice=rule["advice"],
        keywords=rule["keywords"],
        seed=target_date.toordinal(),
    )
    return {
        "date": target_date.isoformat(),
        "pillar": day_pillar["kor"],
        "hanja": day_pillar["hanja"],
        "stem": day_pillar["stem"],
        "branch": day_pillar["branch"],
        "ten_god": ten_god,
        "headline": section["one_line"],
        "summary": rule["summary"],
        "explanation": " ".join(section["easy_explanation"]),
        "advice": " ".join(section["action_advice"]),
        "section": section,
        "keywords": rule["keywords"],
    }
