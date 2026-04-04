"""Quarterly fortune calculation between yearly and monthly flows."""

from __future__ import annotations

from services.interpretation_engine import build_yearly_section
from services.ten_gods import calculate_ten_god_for_stem


QUARTER_DEFINITIONS = [
    {
        "quarter": 1,
        "label": "1분기",
        "window": "입춘~곡우",
        "season": "시작과 계획",
        "element": "wood",
        "element_kor": "목",
        "representative_stem": "갑",
        "phase_lines": [
            "새로운 계획과 방향 설정이 실제 일정으로 옮겨지기 쉬운 구간입니다.",
            "올해 전체 흐름을 열어 가는 출발선이라 무엇을 시작하고 무엇을 보류할지 정하는 힘이 중요합니다.",
        ],
        "focus": ["시작", "계획", "확장성"],
    },
    {
        "quarter": 2,
        "label": "2분기",
        "window": "입하~대서",
        "season": "성장과 갈등",
        "element": "fire",
        "element_kor": "화",
        "representative_stem": "병",
        "phase_lines": [
            "진행 중인 일의 속도와 존재감이 커져 가속도와 마찰이 함께 올라오기 쉬운 구간입니다.",
            "사람과 일의 접점이 늘어나는 만큼 반응 속도보다 조율 감각이 더 중요해질 수 있습니다.",
        ],
        "focus": ["성장", "속도", "조율"],
    },
    {
        "quarter": 3,
        "label": "3분기",
        "window": "입추~상강",
        "season": "결실과 정리",
        "element": "metal",
        "element_kor": "금",
        "representative_stem": "경",
        "phase_lines": [
            "그동안 쌓은 흐름의 성과를 확인하고 남길 것과 덜어낼 것을 나누기 좋은 구간입니다.",
            "결과를 숫자와 기준으로 점검해야 다음 흐름의 실속이 또렷해질 수 있습니다.",
        ],
        "focus": ["결실", "정리", "판단"],
    },
    {
        "quarter": 4,
        "label": "4분기",
        "window": "입동~대한",
        "season": "저장과 휴식",
        "element": "water",
        "element_kor": "수",
        "representative_stem": "임",
        "phase_lines": [
            "겉으로 크게 벌이기보다 내실을 다지고 다음 흐름을 준비하기 좋은 구간입니다.",
            "지금은 에너지를 비축하고 판단 자료를 모으는 쪽이 다음 해의 차이를 크게 만들 수 있습니다.",
        ],
        "focus": ["저장", "회복", "준비"],
    },
]

QUARTER_TEN_GOD_RULES = {
    "비견": {
        "headline": "이번 분기는 내 기준을 분명히 세우는 것이 먼저입니다.",
        "explanation": "같은 기운이 겹쳐 주도권이 강해질 수 있어 방향은 또렷해지지만 조율은 부족해질 수 있습니다.",
        "advice": "시작 전에 역할 선과 우선순위를 먼저 적어 두는 편이 좋습니다.",
        "focus": ["자기기준", "주도권", "역할조정"],
    },
    "겁재": {
        "headline": "이번 분기는 기회보다 분산 관리가 더 중요합니다.",
        "explanation": "사람과 선택지가 늘 수 있지만 동시에 에너지와 지출이 여러 방향으로 흩어질 가능성이 큽니다.",
        "advice": "이번 분기에는 약속, 지출, 일정 상한선을 함께 정하는 편이 좋습니다.",
        "focus": ["분산관리", "경쟁", "선택축소"],
    },
    "식신": {
        "headline": "이번 분기는 작은 결과를 꾸준히 쌓는 쪽이 유리합니다.",
        "explanation": "생산성과 실무력이 붙어 한 번 시작한 일이 실제 결과로 남기 쉬운 흐름입니다.",
        "advice": "매주 하나씩 마감 기록을 남기면 분기 체감이 훨씬 좋아집니다.",
        "focus": ["생산성", "실행", "누적성과"],
    },
    "상관": {
        "headline": "이번 분기는 표현과 변화 욕구를 조절하는 것이 중요합니다.",
        "explanation": "틀을 바꾸고 싶은 마음이 커질 수 있지만 말과 방식이 거칠어지면 마찰도 함께 커질 수 있습니다.",
        "advice": "바꿀 것과 유지할 것을 먼저 나눠 두고 움직이는 편이 좋습니다.",
        "focus": ["표현", "변화", "조율"],
    },
    "편재": {
        "headline": "이번 분기는 바깥 기회를 넓게 보되 선별력이 더 중요합니다.",
        "explanation": "제안, 사람, 외부 흐름이 늘어 판은 넓어질 수 있지만 다 잡으려 하면 성과가 분산되기 쉽습니다.",
        "advice": "이번 분기에는 잡을 기회 두 개만 남기는 식으로 선택 폭을 줄이는 편이 좋습니다.",
        "focus": ["기회", "대외활동", "선별"],
    },
    "정재": {
        "headline": "이번 분기는 축적과 관리 기준을 다지는 데 힘이 실립니다.",
        "explanation": "생활 운영과 재무 기준을 정리할수록 실속이 쌓이고 체감 안정감도 빨리 붙는 흐름입니다.",
        "advice": "분기 예산, 고정비, 저축 비율을 숫자로 정리하는 편이 좋습니다.",
        "focus": ["축적", "관리", "실속"],
    },
    "편관": {
        "headline": "이번 분기는 압박을 관리하며 버티는 힘이 중요합니다.",
        "explanation": "과제가 몰리거나 긴장감이 커질 수 있지만 기준을 잡으면 오히려 돌파력을 만들 수 있습니다.",
        "advice": "무리한 승부보다 체력과 일정 상한선을 정해 두는 편이 좋습니다.",
        "focus": ["압박관리", "도전", "규율"],
    },
    "정관": {
        "headline": "이번 분기는 책임과 평가 기준을 분명히 세우는 것이 좋습니다.",
        "explanation": "공적인 역할과 신뢰 이슈가 부각되기 쉬워 작은 약속과 마감이 크게 읽힐 수 있습니다.",
        "advice": "보여 줄 결과와 지켜야 할 기준을 한 장으로 정리해 두는 편이 좋습니다.",
        "focus": ["책임", "평가", "신뢰"],
    },
    "편인": {
        "headline": "이번 분기는 방향 전환과 탐색을 작게 실험하는 것이 좋습니다.",
        "explanation": "다른 방식이 눈에 들어오는 시기라 전환 감각은 좋지만 너무 많은 선택지를 벌리면 힘이 빠질 수 있습니다.",
        "advice": "새 시도는 한두 개만 남겨 시험해 보는 편이 좋습니다.",
        "focus": ["탐색", "전환", "실험"],
    },
    "정인": {
        "headline": "이번 분기는 준비와 학습을 붙일수록 흐름이 안정됩니다.",
        "explanation": "자료, 공부, 자격, 지원 기반을 채우는 행동이 다음 단계의 체감 차이를 크게 만들 수 있습니다.",
        "advice": "당장 넓히기보다 준비 자산과 자료 축적에 시간을 먼저 쓰는 편이 좋습니다.",
        "focus": ["준비", "학습", "기반다지기"],
    },
}


def calculate_quarterly_fortune(saju_result: dict, target_year: int, target_month: int | None = None) -> dict:
    """Return 4 seasonal fortune blocks for the given target year."""
    day_stem = saju_result["saju"]["day"]["stem"]
    quarters = []
    for quarter_def in QUARTER_DEFINITIONS:
        ten_god = calculate_ten_god_for_stem(day_stem, quarter_def["representative_stem"])
        rule = QUARTER_TEN_GOD_RULES[ten_god]
        explanation = (
            f"{quarter_def['phase_lines'][quarter_def['quarter'] % len(quarter_def['phase_lines'])]} "
            f"{rule['explanation']}"
        )
        advice = (
            f"{rule['advice']} "
            f"특히 {quarter_def['season']} 구간에는 {quarter_def['focus'][0]}보다 {quarter_def['focus'][1]}을 먼저 챙기는 편이 좋습니다."
        )
        focus = _dedupe(rule["focus"] + quarter_def["focus"])[:3]
        section = build_yearly_section(
            headline=rule["headline"],
            explanation=explanation,
            advice=advice,
            focus=focus,
            seed=target_year * 10 + quarter_def["quarter"],
        )
        quarters.append(
            {
                "quarter": quarter_def["quarter"],
                "label": quarter_def["label"],
                "window": quarter_def["window"],
                "season": quarter_def["season"],
                "element": quarter_def["element"],
                "element_kor": quarter_def["element_kor"],
                "ten_god": ten_god,
                "headline": section["one_line"],
                "summary": rule["headline"],
                "explanation": " ".join(section["easy_explanation"]),
                "advice": " ".join(section["action_advice"]),
                "focus": focus,
                "section": section,
            }
        )

    selected_quarter_number = _resolve_selected_quarter(target_month)
    selected_quarter = next((item for item in quarters if item["quarter"] == selected_quarter_number), quarters[0])
    return {
        "year": target_year,
        "quarters": quarters,
        "selected_quarter": selected_quarter,
    }


def _resolve_selected_quarter(target_month: int | None) -> int:
    if target_month in {2, 3, 4}:
        return 1
    if target_month in {5, 6, 7}:
        return 2
    if target_month in {8, 9, 10}:
        return 3
    return 4


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
