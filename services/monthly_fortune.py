"""Monthly fortune calculation using seasonal month pillars."""

from __future__ import annotations

from data.branches import BRANCHES_BY_KOR
from services.saju_calculator import build_korean_datetime, get_year_month_pillars_for_datetime
from services.ten_gods import calculate_ten_god_for_stem

MONTHLY_OPENERS = {
    "비견": [
        "자기 기준을 세워야 흐름이 흔들리지 않는 달입니다.",
        "주도권을 잡되 협업 선을 분명히 하는 편이 좋은 달입니다.",
        "내 방식이 강해지는 만큼 역할 조율이 필요한 달입니다.",
    ],
    "겁재": [
        "경쟁과 분산이 동시에 들어와 선택을 줄여야 하는 달입니다.",
        "주변 변수보다 내 우선순위를 먼저 정리해야 하는 달입니다.",
        "대인 흐름이 넓어지지만 지출과 에너지 분산을 조심할 달입니다.",
    ],
    "식신": [
        "실행과 결과물을 꾸준히 쌓기 좋은 달입니다.",
        "실무 감각을 살리면 성과가 차곡차곡 남는 달입니다.",
        "생산성과 루틴이 맞물리며 손에 잡히는 결과가 나기 쉬운 달입니다.",
    ],
    "상관": [
        "변화 대응과 표현 조절이 중요한 달입니다.",
        "말의 힘이 커지는 만큼 조율과 순서가 필요한 달입니다.",
        "아이디어는 살아나지만 강한 표현은 다듬을 필요가 있는 달입니다.",
    ],
    "편재": [
        "기회 포착과 외부 움직임이 늘어나는 달입니다.",
        "사람과 정보가 넓게 들어와 선택력이 중요해지는 달입니다.",
        "외부 제안이 늘 수 있어 선별 기준이 필요한 달입니다.",
    ],
    "정재": [
        "예산 관리와 안정 축적이 잘 맞는 달입니다.",
        "생활 재무를 정리할수록 안정감이 커지는 달입니다.",
        "무리한 확장보다 관리와 유지가 더 빛나는 달입니다.",
    ],
    "편관": [
        "압박 대응과 일정 관리가 필요한 달입니다.",
        "도전 과제가 늘 수 있어 체력과 규율을 같이 챙겨야 하는 달입니다.",
        "긴장감이 올라와도 원칙을 세우면 흐름을 잡기 좋은 달입니다.",
    ],
    "정관": [
        "책임감과 평가 대응이 강조되는 달입니다.",
        "조직 안에서 신뢰를 쌓기 좋은 달입니다.",
        "기준과 역할이 또렷해져 공적인 흐름이 강해지는 달입니다.",
    ],
    "편인": [
        "방향 전환과 탐색을 병행하기 좋은 달입니다.",
        "새 관점이 열리지만 너무 많은 선택지는 줄이는 편이 좋은 달입니다.",
        "익숙한 방식보다 다른 접근이 통할 가능성이 있는 달입니다.",
    ],
    "정인": [
        "정리, 공부, 지원 기반을 다지기 좋은 달입니다.",
        "배움과 준비가 실제 안정감으로 이어지기 쉬운 달입니다.",
        "안쪽 기반을 단단히 만들면 다음 흐름이 부드러워지는 달입니다.",
    ],
}

ELEMENT_TAILS = {
    "wood": [
        "목 기운이 붙어 새로운 방향과 확장성이 함께 들어옵니다.",
        "목 기운이 실려 관계와 계획을 넓히는 움직임이 살아납니다.",
    ],
    "fire": [
        "화 기운이 얹혀 표현과 속도가 동시에 강해집니다.",
        "화 기운이 살아 반응과 실행 타이밍이 빨라지기 쉽습니다.",
    ],
    "earth": [
        "토 기운이 받쳐 현실 점검과 생활 기준을 잡기 좋습니다.",
        "토 기운이 실려 일상 리듬과 관리력이 안정적으로 붙습니다.",
    ],
    "metal": [
        "금 기운이 겹쳐 기준 정리와 마감 능력이 돋보입니다.",
        "금 기운이 살아 판단과 정리의 선명도가 높아집니다.",
    ],
    "water": [
        "수 기운이 더해져 상황을 읽고 유연하게 조정하기 좋습니다.",
        "수 기운이 흐르며 정보 파악과 타이밍 조절이 중요해집니다.",
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


def calculate_monthly_fortune(saju_result: dict, target_year: int) -> list[dict]:
    """Return 12 monthly fortunes for the given year."""
    day_stem = saju_result["saju"]["day"]["stem"]
    fortunes = []
    used_summaries = set()
    for month in range(1, 13):
        reference_moment = build_korean_datetime(target_year, month, 15, 12, 0)
        month_pillar = get_year_month_pillars_for_datetime(reference_moment)["month"]
        ten_god = calculate_ten_god_for_stem(day_stem, month_pillar["stem"])
        branch_element = BRANCHES_BY_KOR[month_pillar["branch"]]["element"]
        interpretation = _build_monthly_interpretation(ten_god, branch_element, month, used_summaries)
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
) -> dict:
    opener_options = MONTHLY_OPENERS[ten_god]
    tail_options = ELEMENT_TAILS[branch_element]
    for step in range(len(opener_options) * len(tail_options)):
        opener = opener_options[(month + step) % len(opener_options)]
        bridge = MONTHLY_BRIDGES[(month + step) % len(MONTHLY_BRIDGES)]
        tail = tail_options[(month + step) % len(tail_options)]
        headline = f"{opener}"
        if headline not in used_summaries:
            return {
                "headline": headline,
                "summary": f"{opener} {bridge} {tail}",
                "explanation": f"{bridge} {tail}",
                "advice": MONTHLY_ADVICE[ten_god],
            }
    headline = opener_options[month % len(opener_options)]
    return {
        "headline": headline,
        "summary": f"{headline} {MONTHLY_BRIDGES[month % len(MONTHLY_BRIDGES)]} {tail_options[month % len(tail_options)]}",
        "explanation": f"{MONTHLY_BRIDGES[month % len(MONTHLY_BRIDGES)]} {tail_options[month % len(tail_options)]}",
        "advice": MONTHLY_ADVICE[ten_god],
    }
