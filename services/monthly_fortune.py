"""Monthly fortune calculation using seasonal month pillars."""

from __future__ import annotations

from data.branches import BRANCHES_BY_KOR
from services.saju_calculator import build_korean_datetime, get_year_month_pillars_for_datetime
from services.ten_gods import calculate_ten_god_for_stem

MONTHLY_OPENERS = {
    "비견": [
        "내 일과 남의 일을 나눠야 편한 달입니다.",
        "주도권은 잡되 역할 선을 분명히 해야 편한 달입니다.",
        "내 기준이 강해져 협업 규칙도 같이 챙겨야 하는 달입니다.",
    ],
    "겁재": [
        "약속과 지출이 함께 늘 수 있어 선택을 줄여야 하는 달입니다.",
        "사람 문제에 에너지가 퍼지기 쉬워 우선순위가 중요한 달입니다.",
        "주변 흐름이 넓어져도 내 한도를 먼저 정해야 하는 달입니다.",
    ],
    "식신": [
        "미뤄 둔 일과 결과물을 차곡차곡 끝내기 좋은 달입니다.",
        "루틴을 잡고 손에 남는 결과를 만들기 좋은 달입니다.",
        "실무를 꾸준히 밀면 성과가 눈에 보이기 쉬운 달입니다.",
    ],
    "상관": [
        "말과 반응 속도를 조금만 조절하면 훨씬 편한 달입니다.",
        "아이디어는 많아지지만 표현 순서를 다듬어야 하는 달입니다.",
        "답을 빨리 내고 싶어져도 한 번 더 정리하는 편이 좋은 달입니다.",
    ],
    "편재": [
        "제안과 약속이 늘 수 있어 잡을 일부터 골라야 하는 달입니다.",
        "사람과 기회가 넓게 들어와 선별력이 중요한 달입니다.",
        "바깥 움직임이 많아질수록 기준이 있어야 덜 흔들리는 달입니다.",
    ],
    "정재": [
        "예산과 생활 관리를 정리하면 바로 편해지는 달입니다.",
        "무리한 확장보다 지키고 쌓는 쪽이 잘 맞는 달입니다.",
        "돈과 일정 기준을 숫자로 잡아 두면 안정감이 커지는 달입니다.",
    ],
    "편관": [
        "일정과 체력 상한선을 먼저 챙겨야 버틸 수 있는 달입니다.",
        "해야 할 일이 갑자기 늘 수 있어 범위를 줄여야 하는 달입니다.",
        "압박이 느껴져도 원칙과 순서를 세우면 덜 흔들리는 달입니다.",
    ],
    "정관": [
        "약속, 마감, 역할 기준을 잘 지키면 신뢰가 쌓이는 달입니다.",
        "공적인 일에서 책임감이 더 크게 보이는 달입니다.",
        "기준과 역할이 분명해질수록 흐름이 편해지는 달입니다.",
    ],
    "편인": [
        "새 방식을 시험해 보되 바로 갈아타지는 않는 편이 좋은 달입니다.",
        "낯선 선택지가 보여도 비교해 보고 움직이는 쪽이 맞는 달입니다.",
        "다른 접근이 통할 수 있지만 범위는 좁게 잡는 편이 좋은 달입니다.",
    ],
    "정인": [
        "정리, 공부, 준비를 해 두면 다음 달이 훨씬 편해지는 달입니다.",
        "기반을 다지고 배워 두는 시간이 실제 도움으로 돌아오는 달입니다.",
        "안쪽 준비를 해 두면 흐름이 한결 부드러워지는 달입니다.",
    ],
}

ELEMENT_TAILS = {
    "wood": [
        "새 계획이나 방향 전환 이야기가 자주 들어올 수 있습니다.",
        "답을 미루던 일도 다시 꺼내 보게 될 수 있습니다.",
    ],
    "fire": [
        "사람을 만나거나 답을 빨리 정해야 하는 일이 늘 수 있습니다.",
        "반응과 속도가 함께 올라와 하루가 바쁘게 느껴질 수 있습니다.",
    ],
    "earth": [
        "예산, 일정, 생활 기준을 다시 잡아야 할 일이 생기기 쉽습니다.",
        "현실 조건과 버틸 범위를 따져야 마음이 놓이는 흐름입니다.",
    ],
    "metal": [
        "기준, 문서, 마감, 정리 같은 일이 눈에 띄게 늘 수 있습니다.",
        "흩어진 일을 정리하고 끝내는 쪽에서 차이가 날 수 있습니다.",
    ],
    "water": [
        "상황을 조금 더 보고 결정해야 하는 일이 늘 수 있습니다.",
        "사람과 일정 사이에서 조율이 필요한 장면이 잦아질 수 있습니다.",
    ],
}

MONTHLY_BRIDGES = [
    "이번 달은",
    "흐름을 읽으면",
    "무리하게 밀기보다",
    "사람과 일의 간격을 조절하면",
    "기준을 먼저 세우면",
]

MONTHLY_ADVICE = {
    "비견": "혼자 밀기보다 역할 선을 먼저 맞추면 흐름이 안정됩니다.",
    "겁재": "선택지를 줄이고 지출과 약속을 같이 관리하는 편이 좋습니다.",
    "식신": "작은 결과라도 눈에 보이게 마감하면 다음 흐름이 더 좋아집니다.",
    "상관": "강한 말과 빠른 결론은 한 번 더 다듬는 편이 좋습니다.",
    "편재": "제안이 늘수록 잡을 것과 넘길 것을 먼저 나누는 편이 좋습니다.",
    "정재": "예산과 일정 기준을 숫자로 적어 두면 체감 안정감이 커집니다.",
    "편관": "체력과 일정 상한선을 먼저 정해야 흐름이 무너지지 않습니다.",
    "정관": "작은 약속과 마감만 잘 지켜도 평판이 쌓이기 쉬운 달입니다.",
    "편인": "새 선택지는 바로 옮기기보다 시험해 보는 수준으로 다루는 편이 좋습니다.",
    "정인": "배움과 정리에 시간을 배정하면 전체 흐름이 더 부드럽습니다.",
}


def calculate_monthly_fortune(
    saju_result: dict,
    target_year: int,
    analysis_context: dict | None = None,
) -> list[dict]:
    """Return 12 monthly fortunes for the given year."""
    day_stem = saju_result["saju"]["day"]["stem"]
    fortunes = []
    used_summaries = set()
    for month in range(1, 13):
        reference_moment = build_korean_datetime(target_year, month, 15, 12, 0)
        month_pillar = get_year_month_pillars_for_datetime(reference_moment)["month"]
        ten_god = calculate_ten_god_for_stem(day_stem, month_pillar["stem"])
        branch_element = BRANCHES_BY_KOR[month_pillar["branch"]]["element"]
        interpretation = _build_monthly_interpretation(
            ten_god,
            branch_element,
            month,
            used_summaries,
            analysis_context=analysis_context,
        )
        fortunes.append(
            {
                "month": month,
                "pillar": month_pillar["kor"],
                "hanja": month_pillar["hanja"],
                "stem": month_pillar["stem"],
                "branch": month_pillar["branch"],
                "ten_god": ten_god,
                "headline": interpretation["headline"],
                "summary": interpretation["summary"],
                "explanation": interpretation["explanation"],
                "advice": interpretation["advice"],
            }
        )
        used_summaries.add(interpretation["headline"])
    return fortunes


def _build_monthly_interpretation(
    ten_god: str,
    branch_element: str,
    month: int,
    used_summaries: set[str],
    analysis_context: dict | None = None,
) -> dict:
    opener_options = MONTHLY_OPENERS[ten_god]
    tail_options = ELEMENT_TAILS[branch_element]
    for step in range(len(opener_options) * len(tail_options)):
        opener = opener_options[(month + step) % len(opener_options)]
        tail = tail_options[(month + step) % len(tail_options)]
        headline = f"{opener}"
        if headline not in used_summaries:
            advanced = _analysis_context_monthly_lines(analysis_context, month)
            return {
                "headline": headline,
                "summary": f"{opener} {tail} {advanced['summary']}".strip(),
                "explanation": f"{tail} {advanced['explanation']}".strip(),
                "advice": f"{MONTHLY_ADVICE[ten_god]} {advanced['advice']}".strip(),
            }
    headline = opener_options[month % len(opener_options)]
    advanced = _analysis_context_monthly_lines(analysis_context, month)
    return {
        "headline": headline,
        "summary": f"{headline} {tail_options[month % len(tail_options)]} {advanced['summary']}".strip(),
        "explanation": f"{tail_options[month % len(tail_options)]} {advanced['explanation']}".strip(),
        "advice": f"{MONTHLY_ADVICE[ten_god]} {advanced['advice']}".strip(),
    }


def _analysis_context_monthly_lines(analysis_context: dict | None, month: int) -> dict:
    if not analysis_context:
        return {"summary": "", "explanation": "", "advice": ""}

    strength = analysis_context["strength"]
    yongshin = analysis_context["yongshin"]
    flags = analysis_context["flags"]
    primary_phrase = {
        "wood": "막힌 일을 조금씩 열어 두는",
        "fire": "필요한 말과 표현을 분명히 하는",
        "earth": "생활 기준과 예산 범위를 먼저 잡는",
        "metal": "순서와 기준을 먼저 정리하는",
        "water": "바로 확정하지 않고 한 번 더 살피는",
    }.get(yongshin["primary_candidate"], "먼저 기준을 세우는")
    summary = f"{month}월에는 {primary_phrase} 쪽으로 움직일수록 덜 흔들릴 가능성이 큽니다."
    if strength["label"] in {"weak", "slightly_weak"}:
        explanation = "한 번에 많은 일을 벌이기보다, 먼저 끝낼 일과 미룰 일을 나누는 편이 훨씬 편합니다."
    elif strength["label"] in {"strong", "slightly_strong"}:
        explanation = "처음부터 너무 세게 밀기보다 중간 점검을 한 번 넣는 편이 흐름을 덜 흔듭니다."
    else:
        explanation = "일정, 돈, 사람 문제를 한 덩어리로 잡기보다 나눠 다루는 편이 월운을 더 편하게 쓸 수 있습니다."

    if flags["needs_resource_support"]:
        advice = "새 일보다 준비와 정리를 먼저 챙기는 편이 좋습니다."
    elif flags["needs_output_release"]:
        advice = "미뤄 둔 일 하나라도 눈에 보이게 끝내는 편이 좋습니다."
    elif flags["has_luck_pressure"]:
        advice = "사람, 일정, 돈 문제가 겹치면 한 번에 다 처리하려 하지 않는 편이 좋습니다."
    else:
        advice = "욕심나는 일이 많아도 하나씩 끊어 가는 편이 좋습니다."
    return {"summary": summary, "explanation": explanation, "advice": advice}
