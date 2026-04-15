"""Monthly fortune calculation using seasonal month pillars."""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock

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

MONTHLY_STRENGTH_HEADLINE_CLAUSES = {
    "strong": [
        "이번 달은 실행 밀도를 높여도 버티는 힘이 남기 쉬운 편입니다.",
        "핵심 과제를 앞당겨 처리하기 좋은 추진력이 붙는 구간입니다.",
        "압박이 와도 일정 리듬을 유지하기 쉬운 흐름입니다.",
        "중요한 결정 이후 행동까지 연결하기 유리한 편입니다.",
        "확장 과제를 맡아도 무너지지 않는 버팀이 있는 달입니다.",
    ],
    "slightly_strong": [
        "기본 버팀이 있어 핵심 일정 중심 운영이 유리합니다.",
        "초반 정리만 해 두면 중반 이후 실행이 한결 수월해집니다.",
        "무리하지 않아도 중요한 일은 성과로 이어지기 쉬운 흐름입니다.",
        "리듬만 지키면 체감 피로를 낮추며 마감하기 좋습니다.",
        "선택을 줄이고 집중하면 결과 편차를 줄이기 쉽습니다.",
    ],
    "balanced": [
        "확장과 관리의 균형을 맞출수록 월운 체감이 안정됩니다.",
        "속도와 정리 간격을 같이 지키면 실수를 줄이기 쉽습니다.",
        "한쪽으로 몰아치지 않는 운영이 가장 유리한 흐름입니다.",
        "중간 점검을 넣을수록 일정 흔들림을 줄이기 좋습니다.",
        "작은 조정의 반복이 월간 성과를 키우는 달입니다.",
    ],
    "slightly_weak": [
        "범위를 줄여 핵심 일정만 남길수록 안정감이 커집니다.",
        "확장보다 운영 정비를 먼저 두는 편이 더 유리합니다.",
        "결정 속도보다 확인 절차를 강화해야 오차를 줄일 수 있습니다.",
        "한 번에 많이 벌리기보다 단계적으로 닫아 가는 편이 좋습니다.",
        "체력·일정 상한선을 미리 두는 운영이 필요한 달입니다.",
    ],
    "weak": [
        "이번 달은 방어와 회복을 먼저 두는 운영이 실제로 유리합니다.",
        "무리한 확장보다 기존 일정 안정화가 우선인 흐름입니다.",
        "핵심 일정만 남기고 나머지는 조정할수록 손실을 줄일 수 있습니다.",
        "속도를 낮추고 검증 빈도를 높이는 편이 안전합니다.",
        "확정보다 보류를 늘려 피로를 관리하는 선택이 맞습니다.",
    ],
}

MONTHLY_PATTERN_HEADLINE_CLAUSES = {
    "관성격": [
        "기준·역할·마감의 선명도가 결과 차이를 만들 수 있습니다.",
        "책임 분배와 일정 관리가 핵심이 되는 달로 읽힙니다.",
        "평가와 신뢰가 걸린 장면에서 기준 유지가 중요합니다.",
    ],
    "재성격": [
        "돈·시간·자원 배분 기준이 체감 결과를 좌우할 수 있습니다.",
        "기회 선별보다 보존 규칙 정비가 먼저 중요해집니다.",
        "실속이 남는 선택을 고르는 운영이 핵심입니다.",
    ],
    "식상격": [
        "실행과 산출물 마감이 체감 성과를 크게 바꿀 수 있습니다.",
        "아이디어보다 완료 기준 관리가 더 중요해지는 달입니다.",
        "말보다 결과물 누적에서 차이가 벌어지기 쉽습니다.",
    ],
    "인성격": [
        "정보·자료·근거 정리의 완성도가 결과 안정성을 높여 줍니다.",
        "준비 품질이 실행 오차를 줄이는 구조가 강하게 작동합니다.",
        "검토 절차를 고정하면 흔들림을 줄이기 좋습니다.",
    ],
    "비겁격": [
        "사람·협업·경쟁 변수의 경계를 나누는 운영이 중요합니다.",
        "주도권과 분산 관리의 균형이 체감을 크게 바꿀 수 있습니다.",
        "관계 변수 관리가 일정 품질만큼 중요해지는 달입니다.",
    ],
    "균형격": [
        "한쪽으로 치우치지 않는 운영이 가장 큰 강점으로 작동합니다.",
        "무리수보다 일관성이 월간 성과를 안정시킬 수 있습니다.",
        "순서 관리만으로도 체감 난이도를 낮추기 쉬운 흐름입니다.",
    ],
}

MONTHLY_PROFILE_HEADLINE_CLAUSES = {
    "resource_first": [
        "새 일보다 준비·정리 우선 운영이 더 유리한 달입니다.",
        "기초 체계를 먼저 채워 두면 이후 흐름이 편해질 수 있습니다.",
        "먼저 채우고 나중에 넓히는 순서가 맞는 구간입니다.",
    ],
    "output_first": [
        "작은 결과라도 눈에 보이게 끝내는 운영이 유리한 달입니다.",
        "완료 단위를 짧게 가져갈수록 체감 성과가 또렷해질 수 있습니다.",
        "생각보다 마감과 공개를 먼저 두는 편이 맞는 흐름입니다.",
    ],
    "pressure_guard": [
        "사람·일정·돈이 겹치면 범위를 줄이는 방어 운영이 중요합니다.",
        "압박 구간에서는 확장보다 손실 방지 운영이 우선입니다.",
        "충돌 가능성을 낮추는 일정 설계가 핵심인 달입니다.",
    ],
    "balanced_ops": [
        "속도와 회복 간격을 함께 관리하는 균형 운영이 맞습니다.",
        "확정과 보류를 분리하면 체감 피로를 줄일 수 있습니다.",
        "중간 점검 기반 운영이 안정성을 높이는 구간입니다.",
    ],
}

MONTHLY_HEADLINE_TEMPLATES = [
    "{core}",
    "{core} {strength}",
    "{core} {pattern}",
    "{core} {profile}",
    "{pattern} {strength}",
    "{pattern} {profile}",
    "{strength} {profile}",
    "{core} {pattern} {profile}",
    "{core} {strength} {profile}",
    "{core} {pattern} {strength}",
]

MONTHLY_SUMMARY_TEMPLATES = [
    "{headline} {tail}",
    "{headline} {advanced}",
    "{headline} {strength}",
    "{tail} {advanced}",
    "{tail} {strength}",
    "{advanced} {strength}",
    "{headline} {tail} {advanced}",
    "{headline} {advanced} {strength}",
    "{tail} {advanced} {strength}",
    "{headline} {tail} {strength}",
]

MONTHLY_HEADLINE_COOLDOWN_WINDOW = 2
_MONTHLY_RECENT_INDEXES: dict[str, deque[int]] = defaultdict(
    lambda: deque(maxlen=MONTHLY_HEADLINE_COOLDOWN_WINDOW)
)
_MONTHLY_HEADLINE_LOCK = Lock()


def _seed_from_values(*parts: object) -> int:
    total = 0
    for part in parts:
        if part is None:
            continue
        text = str(part)
        total += sum(ord(ch) for ch in text)
    return total


def _pick_seeded(options: list[str], seed: int) -> str:
    return options[seed % len(options)]


def _resolve_monthly_profile_key(analysis_context: dict | None) -> str:
    if not analysis_context:
        return "balanced_ops"
    flags = analysis_context.get("flags", {})
    if flags.get("has_luck_pressure"):
        return "pressure_guard"
    if flags.get("needs_resource_support"):
        return "resource_first"
    if flags.get("needs_output_release"):
        return "output_first"
    return "balanced_ops"


def _monthly_strength_key(analysis_context: dict | None) -> str:
    if not analysis_context:
        return "balanced"
    label = analysis_context.get("strength", {}).get("label", "balanced")
    return label if label in MONTHLY_STRENGTH_HEADLINE_CLAUSES else "balanced"


def _build_monthly_headline_candidates(
    *,
    ten_god: str,
    branch_element: str,
    month: int,
    saju_id: str,
    analysis_context: dict | None,
) -> list[str]:
    base_seed = _seed_from_values(
        saju_id,
        month,
        ten_god,
        branch_element,
        analysis_context.get("strength", {}).get("label", "") if analysis_context else "",
        analysis_context.get("structure", {}).get("primary_pattern", "") if analysis_context else "",
    )
    core_options = MONTHLY_OPENERS[ten_god]
    strength_options = MONTHLY_STRENGTH_HEADLINE_CLAUSES[_monthly_strength_key(analysis_context)]
    pattern_key = (
        analysis_context.get("structure", {}).get("primary_pattern", "균형격")
        if analysis_context
        else "균형격"
    )
    pattern_options = MONTHLY_PATTERN_HEADLINE_CLAUSES.get(
        pattern_key,
        MONTHLY_PATTERN_HEADLINE_CLAUSES["균형격"],
    )
    profile_options = MONTHLY_PROFILE_HEADLINE_CLAUSES[_resolve_monthly_profile_key(analysis_context)]
    tail_options = ELEMENT_TAILS[branch_element]

    candidates: list[str] = []
    seen = set()
    for idx, template in enumerate(MONTHLY_HEADLINE_TEMPLATES):
        sentence = template.format(
            core=_pick_seeded(core_options, base_seed + idx * 3 + 1).rstrip("."),
            strength=_pick_seeded(strength_options, base_seed + idx * 5 + 2).rstrip("."),
            pattern=_pick_seeded(pattern_options, base_seed + idx * 7 + 3).rstrip("."),
            profile=_pick_seeded(profile_options, base_seed + idx * 11 + 4).rstrip("."),
        )
        sentence = " ".join(sentence.split()).strip()
        if not sentence.endswith("."):
            sentence += "."
        # 같은 템플릿 반복을 줄이기 위해 월지 오행 꼬리 문장을 일부 후보에 섞는다.
        if idx in {2, 5, 8}:
            sentence = f"{sentence.rstrip('.')} {_pick_seeded(tail_options, base_seed + idx * 13 + 5)}"
        if sentence not in seen:
            seen.add(sentence)
            candidates.append(sentence)
    return candidates or [MONTHLY_OPENERS[ten_god][0]]


def _pick_monthly_headline(
    *,
    ten_god: str,
    branch_element: str,
    month: int,
    saju_id: str,
    analysis_context: dict | None,
    used_summaries: set[str],
) -> str:
    options = _build_monthly_headline_candidates(
        ten_god=ten_god,
        branch_element=branch_element,
        month=month,
        saju_id=saju_id,
        analysis_context=analysis_context,
    )
    seed = _seed_from_values(saju_id, month, ten_god, branch_element)
    base_index = seed % len(options)
    pattern_key = (
        analysis_context.get("structure", {}).get("primary_pattern", "균형격")
        if analysis_context
        else "균형격"
    )
    strength_key = _monthly_strength_key(analysis_context)
    profile_key = _resolve_monthly_profile_key(analysis_context)
    cooldown_key = f"{saju_id}:{month}:{ten_god}:{branch_element}:{pattern_key}:{strength_key}:{profile_key}"
    with _MONTHLY_HEADLINE_LOCK:
        recent = _MONTHLY_RECENT_INDEXES[cooldown_key]
        for step in range(len(options)):
            candidate_index = (base_index + step) % len(options)
            candidate = options[candidate_index]
            if candidate in used_summaries:
                continue
            if candidate_index in recent and step < len(options) - 1:
                continue
            recent.append(candidate_index)
            return candidate

    return options[base_index]


def _build_monthly_summary(
    *,
    ten_god: str,
    branch_element: str,
    month: int,
    saju_id: str,
    headline: str,
    tail: str,
    advanced: dict,
    analysis_context: dict | None,
) -> str:
    seed = _seed_from_values(
        "monthly_summary",
        saju_id,
        month,
        ten_god,
        branch_element,
        analysis_context.get("strength", {}).get("label", "") if analysis_context else "",
        analysis_context.get("structure", {}).get("primary_pattern", "") if analysis_context else "",
    )
    headline_clause = headline.rstrip(".")
    tail_clause = tail.rstrip(".")
    advanced_clause = (advanced.get("summary") or "").rstrip(".")
    if analysis_context:
        strength_clause = (
            f"중간 계산 기준으로는 {analysis_context['strength']['display_label']} 흐름이라 "
            "확장보다 순서 관리가 체감 차이를 만들기 쉽습니다"
        )
    else:
        strength_clause = "이번 달은 욕심보다 순서와 범위 관리를 먼저 두는 편이 유리합니다"
    if not advanced_clause:
        advanced_clause = "이번 달은 기준을 먼저 고정할수록 흐름을 안정적으로 쓰기 쉽습니다"

    template = MONTHLY_SUMMARY_TEMPLATES[seed % len(MONTHLY_SUMMARY_TEMPLATES)]
    summary = template.format(
        headline=headline_clause,
        tail=tail_clause,
        advanced=advanced_clause,
        strength=strength_clause,
    )
    return f"{' '.join(summary.split()).strip().rstrip('.')}."


def calculate_monthly_fortune(
    saju_result: dict,
    target_year: int,
    analysis_context: dict | None = None,
) -> list[dict]:
    """Return 12 monthly fortunes for the given year."""
    day_stem = saju_result["saju"]["day"]["stem"]
    saju_id = str(saju_result.get("saju_id", ""))
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
            saju_id=saju_id,
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
    saju_id: str,
    analysis_context: dict | None = None,
) -> dict:
    opener_options = MONTHLY_OPENERS[ten_god]
    tail_options = ELEMENT_TAILS[branch_element]
    headline = _pick_monthly_headline(
        ten_god=ten_god,
        branch_element=branch_element,
        month=month,
        saju_id=saju_id,
        analysis_context=analysis_context,
        used_summaries=used_summaries,
    )
    tail = tail_options[month % len(tail_options)]
    advanced = _analysis_context_monthly_lines(analysis_context, month)
    summary = _build_monthly_summary(
        ten_god=ten_god,
        branch_element=branch_element,
        month=month,
        saju_id=saju_id,
        headline=headline,
        tail=tail,
        advanced=advanced,
        analysis_context=analysis_context,
    )
    return {
        "headline": headline,
        "summary": summary,
        "explanation": f"{tail} {advanced['explanation']}".strip(),
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
