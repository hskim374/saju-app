"""Narrative interpretation engine with five-step report sections."""

from __future__ import annotations

from collections import Counter

from data.branches import BRANCHES_BY_KOR
from data.day_pillar_sentences import DAY_PILLAR_SENTENCES, get_day_pillar_sentence_options
from data.stems import STEMS_BY_KOR
from services.analysis_sentence_store import load_analysis_sentences
from services.report_display import (
    format_branch_label,
    format_element_label,
    format_pillar_label,
    format_stem_label,
    format_yin_yang_label,
)
from services.interpretation_rules import build_seed, dominant_story, join_elements, pick_support_elements
from services.interpretation_templates import (
    CAREER_ACTION,
    CAREER_REAL_LIFE,
    CAREER_SUMMARY,
    DAILY_ACTION,
    DAILY_EXPLAIN,
    DAILY_REAL_LIFE,
    DAILY_SUMMARY,
    DECISION_TEMPLATES,
    ELEMENT_STRONG_TEMPLATES,
    ELEMENT_WEAK_TEMPLATES,
    FORTUNE_ACTION,
    FORTUNE_EXPLAIN,
    FORTUNE_REAL_LIFE,
    FORTUNE_SUMMARY,
    HIGHLIGHT_OPENERS,
    MONEY_ACTION,
    MONEY_HABIT_TEMPLATES,
    MONEY_REAL_LIFE,
    MONEY_SUMMARY,
    OPPORTUNITY_TEMPLATES,
    PERSONALITY_ACTION,
    PERSONALITY_REAL_LIFE,
    PERSONALITY_SUMMARY,
    RELATIONSHIP_ACTION,
    RELATIONSHIP_REAL_LIFE,
    RELATIONSHIP_SPEED_TEMPLATES,
    RELATIONSHIP_SUMMARY,
    RISK_TEMPLATES,
    SOCIAL_TEMPLATES,
    SPEECH_TEMPLATES,
    STRENGTH_TEMPLATES,
    STRESS_TEMPLATES,
    TEN_GOD_EXPLANATIONS,
    TRANSITIONS,
    WORK_STYLE_TEMPLATES,
)

REPEAT_GUARD_WORDS = ("안정", "흐름", "기준", "구조")

ELEMENT_TONE = {
    "wood": "방향을 세우고 판을 넓히려는 결",
    "fire": "표현과 존재감",
    "earth": "현실 감각과 버티는 힘",
    "metal": "정리와 결론",
    "water": "흐름을 읽는 감각",
}

DAY_STEM_CORE_LINES = {
    "갑": "일간이 갑목이라 판단할 때 판을 세우고 방향을 먼저 잡으려는 힘이 분명합니다.",
    "을": "일간이 을목이라 바로 밀어붙이기보다 주변 조건을 살피며 유연하게 길을 찾는 편입니다.",
    "병": "일간이 병화라 생각이 정리되면 표현과 실행이 빠르게 밖으로 드러나는 편입니다.",
    "정": "일간이 정화라 분위기와 맥락을 읽은 뒤 필요한 말과 행동을 고르는 편입니다.",
    "무": "일간이 무토라 결정을 내릴 때 버틸 수 있는지와 현실성을 먼저 확인하는 편입니다.",
    "기": "일간이 기토라 사람과 상황을 정리하면서 무리 없는 선택지를 찾는 감각이 살아 있습니다.",
    "경": "일간이 경금이라 모호한 상태를 오래 두기보다 기준을 세우고 결론을 분명히 하려는 편입니다.",
    "신": "일간이 신금이라 디테일과 균형을 살피며 작은 차이에서 판단 포인트를 찾는 편입니다.",
    "임": "일간이 임수라 눈앞의 조건보다 전체 흐름과 가능성을 함께 보며 판단하는 편입니다.",
    "계": "일간이 계수라 겉으로 드러난 말보다 숨은 맥락을 읽고 조용히 방향을 잡는 편입니다.",
}

MONTH_BRANCH_CONTEXT_LINES = {
    "자": "월지가 자수라 생활 리듬에서는 정보 수집과 흐름 파악이 먼저 작동합니다.",
    "축": "월지가 축토라 일과 생활에서 속도보다 버틸 수 있는 틀을 먼저 세우려는 경향이 있습니다.",
    "인": "월지가 인목이라 기본 리듬 자체가 앞으로 나아갈 방향과 확장성을 자주 찾는 편입니다.",
    "묘": "월지가 묘목이라 관계와 생활 리듬에서 부드럽게 조율하며 판을 넓히는 감각이 살아 있습니다.",
    "진": "월지가 진토라 일상에서는 여러 조건을 한 번에 묶어 현실적으로 정리하는 힘이 먼저 나옵니다.",
    "사": "월지가 사화라 평소 리듬에서 반응 속도와 표현 욕구가 비교적 빠르게 올라오는 편입니다.",
    "오": "월지가 오화라 기본 체감이 정적이기보다 움직임과 존재감을 통해 드러나는 편입니다.",
    "미": "월지가 미토라 겉보다 속을 다지고 유지 가능한 방향을 고르는 힘이 일상에 강하게 깔립니다.",
    "신": "월지가 신금이라 생활 전반에서 정리, 마감, 우선순위 설정이 중요한 축으로 자리합니다.",
    "유": "월지가 유금이라 작은 차이와 완성도를 챙기며 결과를 다듬는 감각이 기본값처럼 작동합니다.",
    "술": "월지가 술토라 겉으로는 차분해 보여도 내부에서는 기준과 책임을 분명히 잡으려는 힘이 큽니다.",
    "해": "월지가 해수라 평소에도 한발 먼저 맥락을 읽고 여지를 남겨두는 판단이 잦습니다.",
}

TIME_BRANCH_PRIVATE_LINES = {
    "자": "시지에 자수가 놓이면 겉으로 다 말하지 않아도 속에서는 생각과 계산이 오래 이어지는 편입니다.",
    "축": "시지에 축토가 놓이면 사적인 영역에서는 급히 드러내기보다 안에서 정리한 뒤 움직이려는 성향이 큽니다.",
    "인": "시지에 인목이 놓이면 시간이 갈수록 새로운 방향을 직접 열어 보려는 욕구가 커질 수 있습니다.",
    "묘": "시지에 묘목이 놓이면 가까운 관계일수록 부드럽게 거리를 조절하며 자기 페이스를 지키는 편입니다.",
    "진": "시지에 진토가 놓이면 겉에서는 유연해 보여도 속으로는 여러 선택지를 현실적으로 비교하는 힘이 큽니다.",
    "사": "시지에 사화가 놓이면 친한 사람 앞에서는 표현이 더 빠르고 직선적으로 나오는 편입니다.",
    "오": "시지에 오화가 놓이면 마음이 움직였을 때 에너지와 존재감이 한꺼번에 커지는 편입니다.",
    "미": "시지에 미토가 놓이면 시간이 지날수록 안정과 유지 가능성을 더 중요하게 보는 방향으로 기웁니다.",
    "신": "시지에 신금이 놓이면 가까운 영역일수록 정리 기준과 선을 분명히 세우려는 경향이 드러납니다.",
    "유": "시지에 유금이 놓이면 개인 시간에는 디테일과 완성도를 챙기며 결과를 다듬는 힘이 강합니다.",
    "술": "시지에 술토가 놓이면 나중으로 갈수록 책임감과 버티는 힘이 더 또렷하게 드러나는 편입니다.",
    "해": "시지에 해수가 놓이면 혼자 있을 때 생각의 폭이 넓어지고 선택지를 길게 보는 편입니다.",
}

DECISION_PATTERN_LINES = {
    "갑": "실제로는 선택지를 넓게 펼쳐 본 뒤 한 번 방향을 정하면 쉽게 꺾지 않는 식으로 결정하는 경우가 많습니다.",
    "을": "실제로는 정면 돌파보다 우회로와 조정안을 함께 보며 손실이 적은 선택을 찾는 경우가 많습니다.",
    "병": "실제로는 답이 선명해지는 순간 속도가 붙지만, 답답한 상태가 길어지면 집중력이 급격히 떨어질 수 있습니다.",
    "정": "실제로는 감정선과 분위기를 다 살핀 뒤 말을 고르는 편이라 생각보다 결정이 늦어 보일 수 있습니다.",
    "무": "실제로는 크게 흔들리지 않지만 한 번 아니다 싶으면 완강하게 버티는 식의 반응이 나올 수 있습니다.",
    "기": "실제로는 여러 사람과 조건을 같이 보고 무리가 덜한 쪽으로 선택지를 정리하는 경우가 많습니다.",
    "경": "실제로는 애매한 상태를 오래 참지 않고 기준을 세워 결론부터 정리하려는 모습이 자주 보일 수 있습니다.",
    "신": "실제로는 작은 차이를 오래 비교하다가도 납득되는 기준이 서면 깔끔하게 정리하는 쪽으로 갑니다.",
    "임": "실제로는 하나만 보지 않고 여러 가능성을 동시에 살피다 보니 겉으로는 판단이 느려 보일 수 있습니다.",
    "계": "실제로는 말보다 관찰이 먼저이고, 확신이 들면 조용히 방향을 바꾸는 방식으로 움직이는 경우가 많습니다.",
}

MONTH_BRANCH_WORK_LINES = {
    "자": "일과 돈 문제에서도 먼저 정보를 모으고 흐름을 읽어야 마음이 놓이는 편입니다.",
    "축": "일과 생활에서는 무너지지 않는 기본 틀을 확보해야 비로소 속도가 붙는 편입니다.",
    "인": "기본 리듬이 앞을 향해 있어 같은 자리에서도 더 나은 방향을 자주 찾으려는 경향이 있습니다.",
    "묘": "관계와 협업에서는 정면 충돌보다 부드러운 조율로 공간을 넓히는 방식이 잘 맞습니다.",
    "진": "실무에서는 여러 요소를 한 번에 묶어 현실적으로 정리하는 힘이 강하게 드러나는 편입니다.",
    "사": "상황이 달아오르면 생각보다 빠르게 반응하고 존재감을 드러내는 편입니다.",
    "오": "정적인 환경보다 움직임이 보이는 자리에서 훨씬 힘이 잘 나는 편입니다.",
    "미": "생활 리듬에서는 천천히 다져도 오래 가는 방식을 선호하며, 서두른 변화에는 피로를 느끼기 쉽습니다.",
    "신": "업무에서는 시작보다 정리, 마감, 기준 설정에서 실력이 더 또렷하게 보일 수 있습니다.",
    "유": "돈과 일 모두에서 완성도와 정돈된 결과를 보여야 스스로도 만족하는 편입니다.",
    "술": "맡은 일에서는 책임과 기준이 분명할수록 성과가 안정적으로 이어질 가능성이 큽니다.",
    "해": "겉으로는 조용해도 속으로는 다음 흐름과 여지를 오래 계산하는 편입니다.",
}

PILLAR_ROLE_TITLES = {
    "year": "년주 해석",
    "month": "월주 해석",
    "day": "일주 해석",
    "time": "시주 해석",
}

PILLAR_ROLE_SLOT_LABELS = {
    "year": "년주 자리",
    "month": "월주 자리",
    "day": "일주 자리",
    "time": "시주 자리",
}

PILLAR_ROLE_CORE_LINES = {
    "year": "년주는 바깥에서 읽히는 첫인상과 사회적 배경의 결을 보여 주는 자리입니다.",
    "month": "월주는 생활 리듬과 현실 적응 방식이 가장 먼저 드러나는 자리입니다.",
    "day": "일주는 판단의 중심과 본래 성향이 가장 직접적으로 드러나는 자리입니다.",
    "time": "시주는 가까운 관계와 시간이 흐른 뒤 드러나는 속내를 보여 주는 자리입니다.",
}

PILLAR_ROLE_REAL_LINES = {
    "year": [
        "처음 만나는 자리나 소개를 받는 장면에서는 말보다 분위기와 태도로 이미지가 먼저 정해질 수 있습니다.",
        "면접, 상담, 첫 거래처럼 평가가 빠른 장면에서는 공적인 반응 방식이 생각보다 또렷하게 드러날 수 있습니다.",
        "낯선 조직이나 모임에 들어가면 가까워지기 전까지는 바깥에서 읽히는 캐릭터가 먼저 작동하기 쉽습니다.",
    ],
    "month": [
        "일정이 몰리면 일을 푸는 순서, 쉬는 방식, 생활 루틴에서 기본 운영 리듬이 가장 먼저 드러납니다.",
        "바쁜 주간에는 무엇을 먼저 처리하고 무엇을 미루는지에서 현실 적응 방식이 비교적 선명하게 보입니다.",
        "먹고 일하고 쉬는 반복 장면을 보면 편한 속도와 버티는 기준이 꾸준히 같은 방향으로 나타나는 편입니다.",
    ],
    "day": [
        "회의에서 결론을 빨리 정해야 하거나 선택지를 둘로 좁혀야 할 때 본래 판단 순서가 그대로 올라오기 쉽습니다.",
        "좋고 싫음을 분명히 말해야 하는 순간에는 겉태도보다 내부 판단 기준이 먼저 작동하는 편입니다.",
        "마음은 있어도 바로 움직이지 않는 장면이 생기면 스스로 납득되는 기준을 먼저 맞추고 있는 경우가 많습니다.",
    ],
    "time": [
        "가까운 사람과 서운함이 생기면 겉보다 속에서 정리하는 방식과 거리 조절이 더 선명하게 드러날 수 있습니다.",
        "혼자 쉬는 시간이나 밤에 생각을 정리할 때는 사적인 반응 패턴이 평소보다 더 또렷하게 보일 수 있습니다.",
        "연인이나 가족과 일정, 말투, 거리감을 맞출 때는 속으로 움직이는 판단 순서가 관계 온도를 좌우하기 쉽습니다.",
    ],
}

PILLAR_ROLE_ACTION_LINES = {
    "year": [
        "첫인상과 공적 태도를 의식해야 하는 자리에서는 이 기둥의 장점을 먼저 쓰는 편이 좋습니다.",
        "새로운 환경에 들어갈 때는 보여 줄 태도를 미리 정리해 두는 편이 좋습니다.",
        "바깥 평가가 중요한 시기에는 이 결을 의식적으로 정돈해 쓰는 편이 좋습니다.",
    ],
    "month": [
        "생활과 실무 루틴을 다듬을 때는 이 기둥의 속도에 맞춰 구조를 짜는 편이 좋습니다.",
        "무리한 변화보다 이 기둥이 편해하는 리듬을 먼저 확보하는 편이 좋습니다.",
        "일상 기준을 바꿀 때는 이 결에 맞는 반복 시스템을 먼저 만드는 편이 좋습니다.",
    ],
    "day": [
        "큰 결정일수록 이 기둥이 쓰는 판단 순서를 의식적으로 정리해 두는 편이 좋습니다.",
        "내가 납득하는 방식이 무엇인지 먼저 적어 두면 선택의 질이 올라갈 수 있습니다.",
        "판단 피로를 줄이려면 이 기둥이 강한 영역과 약한 영역을 구분해 쓰는 편이 좋습니다.",
    ],
    "time": [
        "가까운 관계에서는 이 기둥이 만드는 속도 차이를 먼저 설명해 두는 편이 좋습니다.",
        "사적인 판단은 서두르지 말고 이 결이 편한 페이스로 가져가는 편이 좋습니다.",
        "감정이 올라오는 날일수록 이 기둥의 거리 조절 방식을 의식하는 편이 좋습니다.",
    ],
}


def build_interpretation_payload(
    *,
    element_analysis: dict,
    ten_gods: dict | None = None,
    daewoon: dict | None = None,
    year_fortune: dict | None = None,
    saju_result: dict | None = None,
    analysis_context: dict | None = None,
) -> dict:
    """Build story-like sections for the natal chart."""
    page_state = _create_state()
    pillar_profile = _build_pillar_profile(saju_result, ten_gods=ten_gods, daewoon=daewoon)
    seed = build_seed(
        element_analysis["dominant"],
        element_analysis["weak"],
        element_analysis["elements"],
        year_fortune["pillar"] if year_fortune else "",
        pillar_profile["seed_key"],
    )
    overall = _build_overall_section(
        element_analysis,
        ten_gods,
        daewoon,
        year_fortune,
        pillar_profile,
        analysis_context,
        seed,
        page_state,
    )
    personality = _build_personality_section(element_analysis, pillar_profile, analysis_context, seed + 11, page_state)
    wealth = _build_wealth_section(element_analysis, pillar_profile, year_fortune, daewoon, analysis_context, seed + 23, page_state)
    pillar_sections = _build_pillar_sections(
        saju_result=saju_result,
        ten_gods=ten_gods,
        daewoon=daewoon,
        seed=seed + 37,
        state=page_state,
    )
    return {
        "summary": overall["one_line"],
        "personality": _legacy_list(personality),
        "wealth": _legacy_list(wealth),
        "interpretation_sections": {
            "overall": overall,
            "personality": personality,
            "wealth": wealth,
            "pillars": pillar_sections,
        },
    }


def build_report_section(
    *,
    one_line_options: list[str],
    easy_explanation_options: list[str],
    real_life_options: list[str],
    action_advice_options: list[str],
    seed: int,
    used_sentences: dict | set[str] | None = None,
    easy_count: int = 2,
    real_life_count: int = 2,
    action_count: int = 1,
    strength_options: list[str] | None = None,
    risk_options: list[str] | None = None,
    strength_risk_count: int = 2,
    highlight_options: list[str] | None = None,
) -> dict:
    """Build a deterministic five-step section with duplicate avoidance."""
    state = _ensure_state(used_sentences)
    section_used: set[str] = set()
    one_line = _pick_unique(one_line_options, seed, state, section_used)
    easy_explanation = _pick_many(easy_explanation_options, easy_count, seed + 5, state, section_used)
    real_life = _pick_many(real_life_options, real_life_count, seed + 11, state, section_used)
    strength_and_risk = _pick_strength_risk(
        strength_options or [],
        risk_options or [],
        strength_risk_count,
        state,
        seed + 17,
        section_used,
    )
    action_advice = _pick_many(action_advice_options, action_count, seed + 29, state, section_used)
    easy_explanation = _apply_transitions(easy_explanation, seed + 41)
    real_life = _apply_transitions(real_life, seed + 53)
    strength_and_risk = _apply_transitions(strength_and_risk, seed + 67)
    action_advice = _apply_transitions(action_advice, seed + 79)
    highlight = _build_highlight(
        highlight_options or [],
        one_line=one_line,
        easy_explanation=easy_explanation,
        real_life=real_life,
        strength_and_risk=strength_and_risk,
        action_advice=action_advice,
        seed=seed + 83,
    )
    return _section_dict(one_line, highlight, easy_explanation, real_life, strength_and_risk, action_advice)


def create_flow_section(
    *,
    one_line_seed_options: list[str],
    extra_easy_lines: list[str],
    extra_real_life_lines: list[str],
    extra_action_lines: list[str],
    seed: int,
    used_sentences: dict | set[str] | None = None,
    strength_options: list[str] | None = None,
    risk_options: list[str] | None = None,
    highlight_options: list[str] | None = None,
    easy_count: int = 2,
    real_life_count: int = 2,
    action_count: int = 1,
    strength_risk_count: int = 2,
) -> dict:
    """Build a five-step section for yearly/daily/career/relationship style flows."""
    return build_report_section(
        one_line_options=one_line_seed_options,
        easy_explanation_options=extra_easy_lines,
        real_life_options=extra_real_life_lines,
        action_advice_options=extra_action_lines,
        strength_options=strength_options,
        risk_options=risk_options,
        highlight_options=highlight_options,
        seed=seed,
        used_sentences=used_sentences,
        easy_count=easy_count,
        real_life_count=real_life_count,
        action_count=action_count,
        strength_risk_count=strength_risk_count,
    )


def select_ten_god_explanation(ten_god: str, seed: int) -> str:
    """Pick a deterministic explanation sentence for a ten-god label."""
    options = TEN_GOD_EXPLANATIONS[ten_god]
    return options[seed % len(options)]


def _build_overall_section(
    element_analysis: dict,
    ten_gods: dict | None,
    daewoon: dict | None,
    year_fortune: dict | None,
    pillar_profile: dict,
    analysis_context: dict | None,
    seed: int,
    state: dict,
) -> dict:
    dominant = element_analysis["dominant"]
    weak = element_analysis["weak"]
    support = pick_support_elements(element_analysis)
    month_star = ten_gods["ten_gods"].get("month") if ten_gods else None
    current_flow = _current_flow_phrase(year_fortune, daewoon)
    analysis_openings = _analysis_overall_openings(analysis_context, current_flow)
    advanced_easy = _advanced_easy_lines(analysis_context, seed)
    advanced_real = _advanced_real_lines(analysis_context, seed + 3)

    easy_options = [dominant_story(dominant, seed), *advanced_easy, *pillar_profile["overall_easy"]]
    for index, element in enumerate(dominant[:2]):
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[element], seed + index * 5))
    if support:
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[support[0]], seed + 13))
    if weak:
        easy_options.extend(_rotate_pool(ELEMENT_WEAK_TEMPLATES[weak[0]], seed + 19))
    if month_star:
        easy_options.append(select_ten_god_explanation(month_star, seed + 23))
    easy_options.append(current_flow)
    easy_options.extend(_advanced_easy_lines(analysis_context, seed))

    real_life_options = [
        *pillar_profile["overall_real"],
        *advanced_real,
        *_rotate_pool(DECISION_TEMPLATES, seed + 29),
        *_rotate_pool(SOCIAL_TEMPLATES, seed + 37),
        *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 41),
        *_rotate_pool(PERSONALITY_REAL_LIFE, seed + 47),
    ]

    one_line_options = _clean_options([
        *analysis_openings,
        pillar_profile["overall_one_line"],
        f"선택지를 빨리 좁혀야 하는 순간에는 {join_elements(dominant)} 기운 쪽 반응이 먼저 올라와 판단 결이 비교적 또렷하게 보입니다.",
        f"여러 일이 한꺼번에 겹치면 {join_elements(dominant)} 기운이 앞에 서서 생활 전반의 선택 기준을 주도하는 편입니다.",
        f"답을 미루기 어려운 장면에서는 {join_elements(dominant)} 기운이 선명해 일상에서 드러나는 성향의 결이 비교적 분명합니다.",
        f"사람과 조건을 동시에 봐야 할 때는 {join_elements(dominant)} 기운이 주도권을 잡아 쉽게 흔들리기보다 오래 보는 판단이 먼저 들어갑니다.",
        f"결정을 빨리 정리해야 하는 날에는 {join_elements(dominant)} 기운이 중심축이 되어 생각과 행동이 한쪽으로 모이기 쉬운 편입니다.",
    ])
    section = build_report_section(
        one_line_options=one_line_options,
        easy_explanation_options=easy_options,
        real_life_options=real_life_options,
        action_advice_options=[*pillar_profile["overall_action"], *_rotate_pool(PERSONALITY_ACTION, seed + 53)],
        strength_options=_rotate_pool(STRENGTH_TEMPLATES, seed + 59),
        risk_options=_rotate_pool(RISK_TEMPLATES, seed + 67),
        highlight_options=[
            *_advanced_highlight_lines(analysis_context),
            current_flow,
            dominant_story(dominant, seed + 71),
            *_rotate_pool(STRENGTH_TEMPLATES, seed + 73),
        ],
        seed=seed,
        used_sentences=state,
        easy_count=4,
        real_life_count=4,
    )
    _prioritize_section_lines(
        section,
        easy=[*advanced_easy, *pillar_profile["overall_easy"]],
        real=[*advanced_real, *pillar_profile["overall_real"]],
        action=pillar_profile["overall_action"],
    )
    if analysis_openings:
        section["one_line"] = _to_judgment_tone(analysis_openings[0])
        section["headline"] = section["one_line"]
        section["summary"] = section["one_line"]
    return section


def _build_personality_section(
    element_analysis: dict,
    pillar_profile: dict,
    analysis_context: dict | None,
    seed: int,
    state: dict,
) -> dict:
    dominant = element_analysis["dominant"]
    weak = element_analysis["weak"]
    support = pick_support_elements(element_analysis)
    analysis_openings = _analysis_personality_openings(analysis_context)
    advanced_easy = _advanced_easy_lines(analysis_context, seed + 1)
    advanced_real = _advanced_real_lines(analysis_context, seed + 5)
    easy_options = [*advanced_easy, *pillar_profile["personality_easy"]]
    for index, element in enumerate(dominant[:2]):
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[element], seed + index * 5))
    if support:
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[support[0]], seed + 17))
    if weak:
        easy_options.extend(_rotate_pool(ELEMENT_WEAK_TEMPLATES[weak[0]], seed + 23))
    easy_options.append(dominant_story(dominant, seed + 29))

    real_life_options = [
        *pillar_profile["personality_real"],
        *advanced_real,
        *_rotate_pool(SOCIAL_TEMPLATES, seed + 31),
        *_rotate_pool(STRESS_TEMPLATES, seed + 37),
        *_rotate_pool(DECISION_TEMPLATES, seed + 43),
        *_rotate_pool(PERSONALITY_REAL_LIFE, seed + 47),
    ]

    section = build_report_section(
        one_line_options=_clean_options([*analysis_openings, pillar_profile["personality_one_line"], *_rotate_pool(PERSONALITY_SUMMARY, seed)]),
        easy_explanation_options=easy_options,
        real_life_options=real_life_options,
        action_advice_options=[*pillar_profile["personality_action"], *_rotate_pool(PERSONALITY_ACTION, seed + 53)],
        strength_options=_rotate_pool(STRENGTH_TEMPLATES, seed + 59),
        risk_options=_rotate_pool(RISK_TEMPLATES, seed + 67),
        highlight_options=[
            *_analysis_personality_highlights(analysis_context),
            *_advanced_highlight_lines(analysis_context),
            pillar_profile["overall_one_line"],
            *_rotate_pool(STRENGTH_TEMPLATES, seed + 71),
            *_rotate_pool(DECISION_TEMPLATES, seed + 79),
        ],
        seed=seed,
        used_sentences=state,
        easy_count=3,
        real_life_count=4,
    )
    _prioritize_section_lines(
        section,
        easy=[*advanced_easy, *pillar_profile["personality_easy"]],
        real=[*advanced_real, *pillar_profile["personality_real"]],
        action=pillar_profile["personality_action"],
    )
    if analysis_openings:
        section["one_line"] = _to_judgment_tone(analysis_openings[0])
        section["headline"] = section["one_line"]
        section["summary"] = section["one_line"]
    return section


def _build_wealth_section(
    element_analysis: dict,
    pillar_profile: dict,
    year_fortune: dict | None,
    daewoon: dict | None,
    analysis_context: dict | None,
    seed: int,
    state: dict,
) -> dict:
    dominant = element_analysis["dominant"]
    weak = element_analysis["weak"]
    support = pick_support_elements(element_analysis)
    analysis_openings = _analysis_wealth_openings(analysis_context, year_fortune, daewoon)
    advanced_easy = _advanced_easy_lines(analysis_context, seed + 2)
    advanced_real = _advanced_real_lines(analysis_context, seed + 7)
    easy_options = [
        *analysis_openings[1:],
        *advanced_easy,
        dominant_story(dominant, seed + 3),
        *pillar_profile["wealth_easy"],
        _current_flow_phrase(year_fortune, daewoon),
    ]
    for index, element in enumerate(dominant[:2]):
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[element], seed + index * 7))
    if support:
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[support[0]], seed + 13))
    if weak:
        easy_options.extend(_rotate_pool(ELEMENT_WEAK_TEMPLATES[weak[0]], seed + 17))
        if len(weak) > 1:
            easy_options.extend(_rotate_pool(ELEMENT_WEAK_TEMPLATES[weak[1]], seed + 19))

    real_life_options = [
        *pillar_profile["wealth_real"],
        *advanced_real,
        *_rotate_pool(MONEY_REAL_LIFE, seed + 23),
        *_rotate_pool(MONEY_HABIT_TEMPLATES, seed + 29),
        *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 37),
        *_rotate_pool(DECISION_TEMPLATES, seed + 41),
    ]

    section = build_report_section(
        one_line_options=_clean_options([*analysis_openings, pillar_profile["wealth_one_line"], *_rotate_pool(MONEY_SUMMARY, seed)]),
        easy_explanation_options=easy_options,
        real_life_options=real_life_options,
        action_advice_options=[*pillar_profile["wealth_action"], *_rotate_pool(MONEY_ACTION, seed + 43)],
        strength_options=[*pillar_profile.get("wealth_strength", []), *_rotate_pool(STRENGTH_TEMPLATES, seed + 47)],
        risk_options=[*pillar_profile.get("wealth_risk", []), *_rotate_pool(RISK_TEMPLATES, seed + 53)],
        highlight_options=[
            *_analysis_wealth_highlights(analysis_context, year_fortune, daewoon),
            *_advanced_highlight_lines(analysis_context),
            pillar_profile.get("wealth_highlight", ""),
            pillar_profile["wealth_one_line"],
            *_rotate_pool(MONEY_HABIT_TEMPLATES, seed + 59),
            *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 67),
            _current_flow_phrase(year_fortune, daewoon),
        ],
        seed=seed,
        used_sentences=state,
        easy_count=7,
        real_life_count=7,
        action_count=3,
        strength_risk_count=5,
    )
    _prioritize_section_lines(
        section,
        easy=[*advanced_easy, *pillar_profile["wealth_easy"]],
        real=[*advanced_real, *pillar_profile["wealth_real"]],
        action=pillar_profile["wealth_action"],
    )
    section["one_line"] = _to_judgment_tone(analysis_openings[0]) if analysis_openings else pillar_profile["wealth_one_line"]
    section["headline"] = pillar_profile["wealth_one_line"]
    section["summary"] = section["one_line"]
    if analysis_context:
        analysis_highlights = _analysis_wealth_highlights(analysis_context, year_fortune, daewoon)
        if analysis_highlights:
            section["highlight"] = _build_highlight(
                analysis_highlights,
                one_line=section["one_line"],
                easy_explanation=section["easy_explanation"],
                real_life=section["real_life"],
                strength_and_risk=section["strength_and_risk"],
                action_advice=section["action_advice"],
                seed=seed + 61,
            )
            section["highlight_text"] = section["highlight"]
    elif pillar_profile.get("wealth_highlight"):
        section["highlight"] = pillar_profile["wealth_highlight"]
        section["highlight_text"] = pillar_profile["wealth_highlight"]
    section["headline"] = section["one_line"]
    return section


def _build_pillar_sections(
    *,
    saju_result: dict | None,
    ten_gods: dict | None,
    daewoon: dict | None,
    seed: int,
    state: dict,
) -> dict:
    sections = {"year": None, "month": None, "day": None, "time": None}
    if not saju_result:
        return sections

    sentence_data = load_analysis_sentences()
    saju = saju_result.get("saju") or {}
    month_ten_god = ten_gods["ten_gods"].get("month") if ten_gods else None
    active_daewoon_ten_god = daewoon["active_cycle_summary"].get("ten_god") if daewoon else None

    for index, role in enumerate(("year", "month", "day", "time")):
        pillar = saju.get(role)
        if pillar is None:
            continue
        sections[role] = _build_single_pillar_section(
            role=role,
            pillar=pillar,
            sentence_data=sentence_data,
            month_ten_god=month_ten_god,
            active_daewoon_ten_god=active_daewoon_ten_god,
            seed=seed + index * 97,
            state=state,
        )
    return sections


def _build_single_pillar_section(
    *,
    role: str,
    pillar: dict,
    sentence_data: dict,
    month_ten_god: str | None,
    active_daewoon_ten_god: str | None,
    seed: int,
    state: dict,
) -> dict:
    stem = pillar["stem"]
    branch = pillar["branch"]
    stem_meta = STEMS_BY_KOR[stem]
    branch_meta = BRANCHES_BY_KOR[branch]
    day_data = sentence_data["day_stem"].get(stem)
    month_data = sentence_data["month_branch"].get(branch)
    year_data = sentence_data["year_stem"].get(stem)
    time_data = sentence_data["time_branch"].get(branch)
    month_ten_god_data = sentence_data["month_ten_god"].get(month_ten_god) if month_ten_god else None
    daewoon_ten_god_data = sentence_data["daewoon_ten_god"].get(active_daewoon_ten_god) if active_daewoon_ten_god else None

    easy_options = _pillar_easy_options(
        role=role,
        pillar=pillar,
        stem=stem,
        branch=branch,
        stem_meta=stem_meta,
        branch_meta=branch_meta,
        day_data=day_data,
        month_data=month_data,
        year_data=year_data,
        time_data=time_data,
        month_ten_god_data=month_ten_god_data,
        seed=seed,
    )
    real_options = _pillar_real_options(
        role=role,
        pillar=pillar,
        stem=stem,
        branch=branch,
        day_data=day_data,
        month_data=month_data,
        year_data=year_data,
        time_data=time_data,
        seed=seed,
    )
    action_options = _pillar_action_options(
        role=role,
        pillar=pillar,
        stem=stem,
        branch=branch,
        stem_meta=stem_meta,
        branch_meta=branch_meta,
        daewoon_ten_god_data=daewoon_ten_god_data,
        seed=seed,
    )
    strength_options, risk_options = _pillar_strength_risk_options(
        role=role,
        stem_meta=stem_meta,
        branch_meta=branch_meta,
    )
    pillar_label = format_pillar_label(pillar["kor"], pillar.get("hanja"))
    stem_label = format_stem_label(stem)
    branch_label = format_branch_label(branch)
    one_line_options = [
        _pillar_one_line(role, pillar, stem_meta, branch_meta),
        f"{PILLAR_ROLE_TITLES[role]}인 {pillar_label}는 {stem_label} 천간의 {ELEMENT_TONE[stem_meta['element']]}과 {branch_label} 지지의 {ELEMENT_TONE[branch_meta['element']]}이 함께 읽히는 편입니다.",
        f"{pillar_label} {PILLAR_ROLE_TITLES[role].replace(' 해석', '')}는 {stem_label}의 결단 방식과 {branch_label} 지지의 생활 결이 맞물려 비교적 선명한 성향을 만드는 편입니다.",
    ]

    section = build_report_section(
        one_line_options=one_line_options,
        easy_explanation_options=easy_options,
        real_life_options=real_options,
        action_advice_options=action_options,
        seed=seed,
        used_sentences=state,
        easy_count=5,
        real_life_count=5,
        action_count=2,
        strength_options=strength_options,
        risk_options=risk_options,
        strength_risk_count=3,
        highlight_options=[one_line_options[0], *strength_options, *risk_options, *action_options[:2]],
    )
    section["title"] = PILLAR_ROLE_TITLES[role]
    section["pillar"] = pillar["kor"]
    section["role"] = role
    return section


def _build_pillar_profile(
    saju_result: dict | None,
    *,
    ten_gods: dict | None = None,
    daewoon: dict | None = None,
) -> dict:
    empty = {
        "seed_key": "",
        "overall_one_line": "",
        "overall_easy": [],
        "overall_real": [],
        "overall_action": [],
        "personality_one_line": "",
        "personality_easy": [],
        "personality_real": [],
        "personality_action": [],
        "wealth_one_line": "",
        "wealth_highlight": "",
        "wealth_easy": [],
        "wealth_real": [],
        "wealth_action": [],
        "wealth_strength": [],
        "wealth_risk": [],
    }
    if not saju_result:
        return empty

    sentence_data = load_analysis_sentences()
    saju = saju_result.get("saju") or {}
    year = saju.get("year")
    month = saju.get("month")
    day = saju.get("day")
    time = saju.get("time")
    if not year or not month or not day:
        return empty

    day_pillar_data = DAY_PILLAR_SENTENCES.get(day["kor"], {})
    day_pillar_options = {
        "core": get_day_pillar_sentence_options(day["kor"], "core"),
        "relationship": get_day_pillar_sentence_options(day["kor"], "relationship"),
        "wealth": get_day_pillar_sentence_options(day["kor"], "wealth"),
    }
    year_stem_meta = STEMS_BY_KOR[year["stem"]]
    year_branch = BRANCHES_BY_KOR[year["branch"]]
    month_branch = month["branch"]
    day_stem = day["stem"]
    year_stem = year["stem"]
    time_branch = time["branch"] if time else None
    month_ten_god = ten_gods["ten_gods"].get("month") if ten_gods else None
    active_daewoon_ten_god = daewoon["active_cycle_summary"].get("ten_god") if daewoon else None

    day_data = sentence_data["day_stem"][day_stem]
    month_data = sentence_data["month_branch"][month_branch]
    year_data = sentence_data["year_stem"][year_stem]
    time_data = sentence_data["time_branch"].get(time_branch) if time_branch else None
    month_ten_god_data = sentence_data["month_ten_god"].get(month_ten_god) if month_ten_god else None
    daewoon_ten_god_data = sentence_data["daewoon_ten_god"].get(active_daewoon_ten_god) if active_daewoon_ten_god else None
    wealth_profile = _resolve_wealth_profile(day_stem, month_branch, month_ten_god)

    base_seed = build_seed(
        year["kor"],
        month["kor"],
        day["kor"],
        time["kor"] if time else "",
        month_ten_god or "",
        active_daewoon_ten_god or "",
    )

    overall_easy = [
        f"답을 빨리 정해야 하는 장면에서는 {_strip_day_pillar_prefix(_pick_profile_line(day_pillar_options['core'], base_seed + 1), day['kor']) or '판단 순서가 비교적 또렷하게 드러나는 편입니다.'}",
        f"낯선 자리에서는 {_pick_profile_line(year_data['first_impression'], base_seed + 5).lower()}",
        _pick_profile_line(day_data["social_reaction"], base_seed + 3),
        MONTH_BRANCH_WORK_LINES[month_branch],
        DAY_STEM_CORE_LINES[day_stem],
        _build_year_pillar_line(year["kor"], year_stem_meta["element"], year_branch["element"]),
    ]
    if time_branch:
        overall_easy.append(TIME_BRANCH_PRIVATE_LINES[time_branch])
    if month_ten_god_data:
        overall_easy.append(_as_modifier_line("성격 보정으로 보면", _pick_profile_line(month_ten_god_data["personality_modifier"], base_seed + 7)))

    overall_real = [
        f"회의에서 선택지를 둘 이상 놓고 결론을 정해야 할 때는 {_strip_day_pillar_prefix(_pick_profile_line(day_pillar_options['core'], base_seed + 2), day['kor']) or '판단의 중심축이 비교적 분명하게 드러나는 편입니다.'}",
        DECISION_PATTERN_LINES[day_stem],
        MONTH_BRANCH_WORK_LINES[month_branch],
        _pick_profile_line(day_data["speech_style"], base_seed + 11),
        _pick_profile_line(month_data["work_adaptation"], base_seed + 13),
        _build_year_real_life_line(year["kor"], year_branch["kor"]),
    ]
    if time_branch:
        overall_real.append(_pick_profile_line(time_data["intimate_reaction"], base_seed + 17))

    overall_action = []
    if daewoon_ten_god_data:
        overall_action.append(_pick_profile_line(daewoon_ten_god_data["action_advice"], base_seed + 19))

    personality_easy = [
        f"처음 만난 사람과 금방 호흡을 맞춰야 하는 자리에서는 {_strip_day_pillar_prefix(_pick_profile_line(day_pillar_options['core'], base_seed + 21), day['kor']) or '기본 반응 순서가 먼저 드러나는 편입니다.'}",
        _pick_profile_line(day_data["social_reaction"], base_seed + 31),
    ]
    if month_ten_god_data:
        personality_easy.append(_as_modifier_line("성격 보정으로 보면", _pick_profile_line(month_ten_god_data["personality_modifier"], base_seed + 29)))
    personality_easy.extend([
        _pick_profile_line(month_data["base_personality"], base_seed + 23),
    ])
    personality_easy.append(DAY_STEM_CORE_LINES[day_stem])
    personality_easy.append(MONTH_BRANCH_CONTEXT_LINES[month_branch])
    personality_real = [
        f"가까운 사람과 의견이 갈리거나 내 입장을 설명해야 하는 장면에서는 {_strip_day_pillar_prefix(_pick_profile_line(day_pillar_options['relationship'], base_seed + 24), day['kor']) or '관계에서도 기본 반응 순서가 선명한 편입니다.'}",
        _build_personality_social_line(year["kor"], time_branch),
        DECISION_PATTERN_LINES[day_stem],
        _pick_profile_line(day_data["social_reaction"], base_seed + 31),
        _pick_profile_line(day_data["speech_style"], base_seed + 37),
    ]
    if time_branch:
        personality_real.append(_pick_profile_line(time_data["intimate_reaction"], base_seed + 41))
    personality_action = []
    if daewoon_ten_god_data:
        personality_action.append(_pick_profile_line(daewoon_ten_god_data["action_advice"], base_seed + 43))

    wealth_easy = [
        f"큰 지출이나 계약을 앞두면 {_strip_day_pillar_prefix(_pick_profile_line(day_pillar_options['wealth'], base_seed + 45), day['kor']) or '돈 문제에서도 본래 판단 순서가 먼저 올라오는 편입니다.'}",
        _build_wealth_profile_easy_line(wealth_profile, day_stem, month_branch),
        _pick_profile_line(month_data["money_habit"], base_seed + 47),
        MONTH_BRANCH_WORK_LINES[month_branch],
        _build_wealth_base_line(day["kor"], month["kor"]),
    ]
    if month_ten_god_data:
        wealth_easy.append(_as_modifier_line("재물 보정으로 보면", _pick_profile_line(month_ten_god_data["wealth_modifier"], base_seed + 53)))
    wealth_real = [
        f"결제나 투자 여부를 바로 정해야 하는 장면에서는 {_strip_day_pillar_prefix(_pick_profile_line(day_pillar_options['wealth'], base_seed + 48), day['kor']) or '돈 문제에서도 본래 판단 결이 크게 작동하는 편입니다.'}",
        _build_wealth_real_life_line(day_stem, month_branch),
        _build_wealth_profile_real_line(wealth_profile, day_stem, month_branch),
        _pick_profile_line(month_data["work_adaptation"], base_seed + 59),
        _build_year_resource_line(year["kor"], year_stem_meta["element"]),
    ]
    if time_branch:
        wealth_real.append(_build_time_resource_line(time["kor"], time_branch))
    wealth_action = []
    if daewoon_ten_god_data:
        wealth_action.append(_pick_profile_line(daewoon_ten_god_data["action_advice"], base_seed + 61))
    wealth_action.append(_build_wealth_profile_action_line(wealth_profile, month_branch))

    return {
        "seed_key": "".join(
            pillar["kor"] for pillar in [year, month, day] + ([time] if time else [])
        ),
        "overall_one_line": (
            f"답을 빨리 정해야 하는 순간에는 {day['kor']}의 판단 결과 {month['branch']}의 생활 리듬이 함께 올라와 "
            "무슨 기준을 먼저 잡는지가 비교적 또렷하게 드러나는 편입니다."
        ),
        "overall_easy": overall_easy,
        "overall_real": overall_real,
        "overall_action": overall_action,
        "personality_one_line": (
            f"사람을 가까이 둘지 거리를 둘지 정해야 하는 장면에서는 {day['kor']}의 판단 순서와 "
            f"{month['branch']}의 생활 리듬이 먼저 드러나는 편입니다."
        ),
        "personality_easy": personality_easy,
        "personality_real": personality_real,
        "personality_action": personality_action,
        "wealth_one_line": _build_wealth_profile_one_line(wealth_profile, month["kor"], day["kor"]),
        "wealth_highlight": _build_wealth_profile_highlight_line(wealth_profile),
        "wealth_easy": wealth_easy,
        "wealth_real": wealth_real,
        "wealth_action": wealth_action,
        "wealth_strength": [_build_wealth_profile_strength_line(wealth_profile)],
        "wealth_risk": [_build_wealth_profile_risk_line(wealth_profile)],
    }


def _resolve_wealth_profile(day_stem: str, month_branch: str, month_ten_god: str | None) -> str:
    if month_ten_god in {"정재", "정관"} or month_branch in {"축", "미", "술"}:
        return "system_saver"
    if month_ten_god in {"편재"} or month_branch in {"인", "묘"}:
        return "selective_expander"
    if day_stem in {"경", "신"} or month_branch in {"신", "유"}:
        return "precision_controller"
    if day_stem in {"임", "계"} or month_branch in {"자", "해"}:
        return "flow_observer"
    if month_ten_god in {"식신", "상관"} or day_stem in {"병", "정"}:
        return "opportunity_handler"
    return "steady_accumulator"


def _build_wealth_profile_one_line(profile: str, month_kor: str, day_kor: str) -> str:
    lines = {
        "system_saver": f"돈이 들어오거나 나갈 때는 {month_kor}의 운영 감각과 {day_kor}의 판단 순서가 함께 작동해, 버는 힘보다 관리 기준에서 차이가 크게 나는 편입니다.",
        "selective_expander": f"새 수입처나 제안이 보이면 {month_kor}와 {day_kor}의 결이 함께 올라와, 기회를 넓히는 힘보다 무엇을 고를지에 따라 결과가 갈리는 편입니다.",
        "precision_controller": f"정산이나 마감이 걸린 장면에서는 {month_kor}와 {day_kor}의 결이 같이 작동해, 속도보다 정리와 통제력에서 실제 차이가 크게 나는 편입니다.",
        "flow_observer": f"큰 지출이나 투자 판단 앞에서는 {month_kor}와 {day_kor}의 결이 같이 올라와, 눈앞 금액보다 전체 흐름을 어떻게 읽느냐에 따라 안정감이 달라지는 편입니다.",
        "opportunity_handler": f"수입 기회가 들어오면 {month_kor}와 {day_kor}의 결이 같이 움직여, 그 기회를 어떻게 활용하고 마무리하느냐에 따라 성과가 갈리는 편입니다.",
        "steady_accumulator": f"돈 문제를 오래 끌고 갈수록 {month_kor}와 {day_kor}의 결이 함께 작동해, 감정 반응보다 운영 습관과 판단 순서가 먼저 힘을 쓰는 편입니다.",
    }
    return lines[profile]


def _build_wealth_profile_highlight_line(profile: str) -> str:
    return {
        "system_saver": "돈은 크게 늘리는 힘보다 기준을 지키는 힘에서 차이가 크게 납니다.",
        "selective_expander": "문제는 수입 기회 자체보다 무엇을 남길 선택을 하느냐입니다.",
        "precision_controller": "재물은 감각보다 정리와 분리 기준에서 더 분명하게 갈립니다.",
        "flow_observer": "돈은 눈앞 숫자보다 전체 흐름을 얼마나 길게 보느냐에서 체감이 달라집니다.",
        "opportunity_handler": "수입 기회는 들어와도 마무리 기준이 없으면 결과가 흐려지기 쉽습니다.",
        "steady_accumulator": "재물은 한 번에 크게 움직이기보다 꾸준히 남기는 방식에서 강점이 드러납니다.",
    }[profile]


def _build_wealth_profile_easy_line(profile: str, day_stem: str, month_branch: str) -> str:
    lines = {
        "system_saver": f"일간 {day_stem}과 월지 {month_branch}의 조합을 보면, 돈 문제에서도 먼저 기준표와 유지 가능성을 확인해야 안정감이 생기는 편입니다.",
        "selective_expander": f"일간 {day_stem}과 월지 {month_branch}의 조합을 보면, 수입처를 넓히는 능력은 있어도 선별 기준이 없으면 흐름이 쉽게 퍼질 수 있습니다.",
        "precision_controller": f"일간 {day_stem}과 월지 {month_branch}의 조합을 보면, 재정도 큰 판보다 세부 정리와 통제에서 힘이 살아나는 편입니다.",
        "flow_observer": f"일간 {day_stem}과 월지 {month_branch}의 조합을 보면, 재물 문제도 바로 결론내리기보다 흐름을 읽고 타이밍을 보는 쪽이 더 잘 맞습니다.",
        "opportunity_handler": f"일간 {day_stem}과 월지 {month_branch}의 조합을 보면, 벌 기회는 보이지만 끝까지 남기려면 관리 규칙을 함께 세워야 하는 편입니다.",
        "steady_accumulator": f"일간 {day_stem}과 월지 {month_branch}의 조합을 보면, 돈 문제도 속도보다 반복 가능한 습관이 실제 체감 차이를 만드는 편입니다.",
    }
    return lines[profile]


def _build_wealth_profile_real_line(profile: str, day_stem: str, month_branch: str) -> str:
    lines = {
        "system_saver": "현실에서는 들어오는 돈보다 고정비, 지출 기준, 반복 관리 루틴이 결과를 훨씬 크게 좌우할 가능성이 큽니다.",
        "selective_expander": "현실에서는 기회가 보여도 다 잡지 않고 몇 개만 선별해야 실제로 남는 결과가 생기기 쉽습니다.",
        "precision_controller": "현실에서는 시작보다 마감, 정산, 분리 계좌, 우선순위 정리 같은 장면에서 차이가 더 크게 드러날 수 있습니다.",
        "flow_observer": "현실에서는 바로 투자나 지출 결정을 내리기보다 한 템포 늦춰 전체 흐름을 보는 날에 실수를 줄이기 쉽습니다.",
        "opportunity_handler": "현실에서는 수입 기회가 늘어도 정리 기준이 없으면 체감 성과가 남지 않을 가능성이 큽니다.",
        "steady_accumulator": "현실에서는 큰 한 방보다 월 단위로 누적되는 관리 습관이 훨씬 큰 차이를 만들 가능성이 큽니다.",
    }
    return lines[profile]


def _build_wealth_profile_action_line(profile: str, month_branch: str) -> str:
    lines = {
        "system_saver": f"월지 {month_branch}의 생활 리듬을 기준으로 보면 예산표, 고정비 점검일, 자동이체처럼 흔들리지 않는 틀을 먼저 세우는 편이 좋습니다.",
        "selective_expander": f"월지 {month_branch}의 리듬을 기준으로 보면 새 기회를 늘리기 전에 무엇을 버릴지부터 정하는 편이 재정 분산을 줄이기 쉽습니다.",
        "precision_controller": f"월지 {month_branch}의 결을 기준으로 보면 계좌 분리와 마감 기준을 먼저 고정하는 편이 체감 안정에 더 빠르게 연결됩니다.",
        "flow_observer": f"월지 {month_branch}의 리듬을 기준으로 보면 큰 돈 판단은 하루 이상 간격을 두고 다시 보는 편이 더 안전합니다.",
        "opportunity_handler": f"월지 {month_branch}의 생활 결을 기준으로 보면 수입 기회 하나를 늘릴 때 지출 통제 규칙도 동시에 붙이는 편이 좋습니다.",
        "steady_accumulator": f"월지 {month_branch}의 리듬을 기준으로 보면 수입 확대보다 새는 흐름을 막는 점검부터 시작하는 편이 더 효과적입니다.",
    }
    return lines[profile]


def _build_wealth_profile_strength_line(profile: str) -> str:
    return {
        "system_saver": "한 번 기준을 세우면 쉽게 흐트러지지 않아 안정적인 축적에 강점이 있습니다.",
        "selective_expander": "기회 자체를 보는 눈은 살아 있어 선택만 잘하면 수입 폭을 넓힐 여지가 있습니다.",
        "precision_controller": "정리와 통제력이 붙으면 재정 안정이 생각보다 빠르게 올라갈 수 있습니다.",
        "flow_observer": "서두르지 않고 흐름을 읽는 힘이 있어 큰 실수를 줄이는 데 강점이 있습니다.",
        "opportunity_handler": "기회 대응력과 실무 감각이 같이 붙으면 수입을 현실 성과로 바꾸는 힘이 있습니다.",
        "steady_accumulator": "꾸준히 쌓는 구조를 만들면 장기 누적에서 강점이 분명하게 드러납니다.",
    }[profile]


def _build_wealth_profile_risk_line(profile: str) -> str:
    return {
        "system_saver": "기준 정리만 오래 하다 보면 실제 확장 시점을 놓칠 수 있습니다.",
        "selective_expander": "기회가 많아질수록 선별 기준이 흐려지면 결과가 쉽게 분산될 수 있습니다.",
        "precision_controller": "정리와 통제를 지나치게 오래 잡으면 실행 자체가 늦어질 수 있습니다.",
        "flow_observer": "흐름을 오래 보려는 성향이 강하면 결론과 실행이 함께 늦어질 수 있습니다.",
        "opportunity_handler": "수입 기회를 벌이는 속도에 비해 마무리 기준이 약하면 남는 결과가 줄어들 수 있습니다.",
        "steady_accumulator": "안정 운영이 강점이지만 너무 유지 쪽으로 기울면 확장 타이밍을 놓칠 수 있습니다.",
    }[profile]


def _pillar_one_line(role: str, pillar: dict, stem_meta: dict, branch_meta: dict) -> str:
    return (
        f"{PILLAR_ROLE_TITLES[role]}인 {format_pillar_label(pillar['kor'], pillar.get('hanja'))}는 "
        f"{ELEMENT_TONE[stem_meta['element']]}과 {ELEMENT_TONE[branch_meta['element']]}이 함께 드러나는 자리입니다."
    )


def _pillar_easy_options(
    *,
    role: str,
    pillar: dict,
    stem: str,
    branch: str,
    stem_meta: dict,
    branch_meta: dict,
    day_data: dict | None,
    month_data: dict | None,
    year_data: dict | None,
    time_data: dict | None,
    month_ten_god_data: dict | None,
    seed: int,
) -> list[str]:
    day_pillar_data = DAY_PILLAR_SENTENCES.get(pillar["kor"], {}) if role == "day" else None
    pillar_label = format_pillar_label(pillar["kor"], pillar.get("hanja"))
    stem_label = format_stem_label(stem)
    branch_label = format_branch_label(branch)
    yin_yang_label = format_yin_yang_label(stem_meta["yin_yang"])
    options = [
        PILLAR_ROLE_CORE_LINES[role],
        f"{pillar_label}는 천간 {stem_label}의 {ELEMENT_TONE[stem_meta['element']]}과 지지 {branch_label}의 {ELEMENT_TONE[branch_meta['element']]}이 한 자리에서 만나 성향의 결을 또렷하게 만드는 편입니다.",
        f"{pillar_label}를 보면 {yin_yang_label} 성향의 {stem_label} 천간이 앞에 서고, {branch_label} 지지가 현실 반응의 속도를 조절하는 편입니다.",
        f"이 기둥에서는 {stem_label}의 기질과 {branch_label} 지지의 생활 결이 겹쳐 같은 상황도 특정한 방식으로 읽히기 쉽습니다.",
        f"{PILLAR_ROLE_TITLES[role].replace(' 해석', '')}를 세밀하게 보면, {stem_label}은 판단의 출발점을 만들고 {branch_label}는 실제 반응의 리듬을 정하는 편입니다.",
    ]
    if role == "year":
        options.extend([
            _build_year_pillar_line(pillar["kor"], stem_meta["element"], branch_meta["element"]),
            _pick_profile_line(year_data["first_impression"], seed + 3) if year_data else "",
        ])
    elif role == "month":
        options.extend([
            MONTH_BRANCH_CONTEXT_LINES[branch],
            _pick_profile_line(month_data["base_personality"], seed + 5) if month_data else "",
            _pick_profile_line(month_data["work_adaptation"], seed + 7) if month_data else "",
        ])
    elif role == "day":
        options.extend([
            day_pillar_data.get("core", "") if day_pillar_data else "",
            DAY_STEM_CORE_LINES[stem],
            _pick_profile_line(day_data["social_reaction"], seed + 11) if day_data else "",
            _pick_profile_line(day_data["speech_style"], seed + 13) if day_data else "",
        ])
    elif role == "time":
        options.extend([
            TIME_BRANCH_PRIVATE_LINES[branch],
            _pick_profile_line(time_data["intimate_reaction"], seed + 17) if time_data else "",
            f"시주 {pillar_label}는 시간이 갈수록 드러나는 사적인 반응 결을 설명할 때 특히 중요하게 읽히는 편입니다.",
        ])
    if month_ten_god_data:
        options.append(_as_modifier_line("월간 십성 보정으로 보면", _pick_profile_line(month_ten_god_data["personality_modifier"], seed + 19)))
    return [item for item in options if item]


def _pillar_real_options(
    *,
    role: str,
    pillar: dict,
    stem: str,
    branch: str,
    day_data: dict | None,
    month_data: dict | None,
    year_data: dict | None,
    time_data: dict | None,
    seed: int,
) -> list[str]:
    day_pillar_data = DAY_PILLAR_SENTENCES.get(pillar["kor"], {}) if role == "day" else None
    pillar_label = format_pillar_label(pillar["kor"], pillar.get("hanja"))
    stem_label = format_stem_label(stem)
    branch_label = format_branch_label(branch)
    options = [
        *_rotate_pool(PILLAR_ROLE_REAL_LINES[role], seed + 3),
        f"같은 부탁을 받아도 먼저 판단하는 순서는 {stem_label} 쪽에서 올라오고, 실제로 움직이는 속도는 {branch_label} 리듬을 크게 벗어나지 않는 편입니다.",
        f"선택지가 두세 개 동시에 올라오면 {branch_label} 쪽 생활 리듬을 기준으로 버틸 수 있는지부터 살피는 장면이 반복되기 쉽습니다.",
        f"급하게 결론을 내야 할 때도 반응 방식은 {stem_label}의 판단 순서와 {branch_label}의 생활 속도가 겹친 방향으로 비교적 일정하게 나타납니다.",
    ]
    if role == "year":
        options.extend([
            _build_year_real_life_line(pillar["kor"], branch),
            _pick_profile_line(year_data["first_impression"], seed + 23) if year_data else "",
        ])
    elif role == "month":
        options.extend([
            MONTH_BRANCH_WORK_LINES[branch],
            _pick_profile_line(month_data["money_habit"], seed + 29) if month_data else "",
            _pick_profile_line(month_data["work_adaptation"], seed + 31) if month_data else "",
        ])
    elif role == "day":
        day_core = _strip_day_pillar_prefix(day_pillar_data.get("core", ""), pillar["kor"]) if day_pillar_data else ""
        options.extend([
            f"중요한 결정을 바로 정해야 하는 장면에서는 {day_core or '판단의 중심 결이 비교적 선명하게 올라오는'} 쪽으로 반응하기 쉽습니다.",
            DECISION_PATTERN_LINES[stem],
            _pick_profile_line(day_data["speech_style"], seed + 37) if day_data else "",
            _pick_profile_line(day_data["social_reaction"], seed + 41) if day_data else "",
        ])
    elif role == "time":
        options.extend([
            _pick_profile_line(time_data["intimate_reaction"], seed + 43) if time_data else "",
            f"가까운 관계로 갈수록 시지 {branch}가 만든 거리 조절과 속도 차이가 더 분명하게 체감될 가능성이 큽니다.",
            f"혼자 판단하는 단계에서는 시주 {pillar_label}가 보여 주는 내면의 정리 방식이 더 자주 드러날 수 있습니다.",
        ])
    return [item for item in options if item]


def _pillar_action_options(
    *,
    role: str,
    pillar: dict,
    stem: str,
    branch: str,
    stem_meta: dict,
    branch_meta: dict,
    daewoon_ten_god_data: dict | None,
    seed: int,
) -> list[str]:
    pillar_label = format_pillar_label(pillar["kor"], pillar.get("hanja"))
    stem_label = format_stem_label(stem)
    branch_label = format_branch_label(branch)
    options = [
        *_rotate_pool(PILLAR_ROLE_ACTION_LINES[role], seed + 5),
        f"{pillar_label}의 장점을 살리려면 {format_element_label(stem_meta['element'])} 기운이 강해지는 순간에는 밀어붙일 기준을, {format_element_label(branch_meta['element'])} 기운이 강해지는 순간에는 조절 기준을 같이 두는 편이 좋습니다.",
        f"{PILLAR_ROLE_SLOT_LABELS[role]}의 {pillar_label}를 실제 선택에 쓰려면 {stem_label}이 강해지는 순간과 {branch_label}가 반응하는 순간을 구분해서 보는 편이 좋습니다.",
    ]
    if daewoon_ten_god_data:
        options.append(_pick_profile_line(daewoon_ten_god_data["action_advice"], seed + 7))
    return [item for item in options if item]


def _pillar_strength_risk_options(role: str, stem_meta: dict, branch_meta: dict) -> tuple[list[str], list[str]]:
    strengths = [
        f"{PILLAR_ROLE_TITLES[role].replace(' 해석', '')}에서 {format_element_label(stem_meta['element'])} 기운이 앞에 서면 판단의 방향성이 비교적 선명해지는 강점이 있습니다.",
        f"{format_element_label(branch_meta['element'])} 지지가 받쳐 주면 실제 생활에서 {ELEMENT_TONE[branch_meta['element']]}이 결과로 이어지기 쉬운 장점이 있습니다.",
        f"{format_yin_yang_label(stem_meta['yin_yang'])} 성향의 천간이 있어 반응 리듬이 일정한 편이라 역할을 오래 유지할 때 장점이 살아나기 쉽습니다.",
        f"{PILLAR_ROLE_TITLES[role].replace(' 해석', '')}가 또렷할수록 자신의 방식과 현실 반응을 연결하는 힘이 좋아질 수 있습니다.",
    ]
    risks = [
        f"다만 {format_element_label(stem_meta['element'])} 쪽 힘이 강하게만 쓰이면 판단이 한쪽으로 쏠릴 수 있어 반대 조건을 같이 보는 편이 좋습니다.",
        f"{format_element_label(branch_meta['element'])} 지지가 과하게 작동하면 속도나 거리감이 고정되어 융통성이 줄어들 수 있습니다.",
        f"{PILLAR_ROLE_TITLES[role].replace(' 해석', '')}의 결을 의식하지 않으면 같은 패턴을 반복해 기회 판단이 늦어질 수 있습니다.",
        f"{format_element_label(stem_meta['element'])}과 {format_element_label(branch_meta['element'])}의 장단을 같이 보지 않으면 장점이 오히려 부담으로 바뀔 수 있습니다.",
    ]
    return strengths, risks


def _build_year_pillar_line(year_pillar: str, stem_element: str, branch_element: str) -> str:
    return (
        f"년주가 {year_pillar}라 바깥에서 보이는 첫인상에는 "
        f"{ELEMENT_TONE[stem_element]}과 {ELEMENT_TONE[branch_element]}이 함께 묻어나는 편입니다."
    )


def _build_year_real_life_line(year_pillar: str, year_branch: str) -> str:
    return (
        f"처음 보는 사람과 일을 시작하거나 소개를 받는 장면에서는 "
        f"{year_branch} 쪽 바깥 반응이 먼저 읽혀 첫인상이 비교적 빨리 정해지는 편입니다."
    )


def _build_personality_social_line(year_pillar: str, time_branch: str | None) -> str:
    if time_branch:
        return (
            "처음 만난 자리에서는 공적인 태도가 먼저 보이지만, "
            "가까워질수록 답장 속도와 거리 조절 같은 사적인 페이스가 더 또렷하게 드러날 수 있습니다."
        )
    return "처음에는 차분하고 공적인 태도가 먼저 보이지만, 친해질수록 마음을 여는 속도는 생각보다 천천히 드러나는 편입니다."


def _build_wealth_base_line(day_pillar: str, month_pillar: str) -> str:
    return (
        f"일주 {day_pillar}와 월주 {month_pillar}를 같이 보면, "
        "재물은 크게 벌리는 힘보다 반복 가능한 관리 습관이 결과를 더 크게 좌우하는 편입니다."
    )


def _build_wealth_real_life_line(day_stem: str, month_branch: str) -> str:
    return (
        f"돈 문제에서는 바로 결제하거나 투자하기보다 "
        f"{day_stem} 쪽 판단 순서와 {month_branch} 쪽 생활 리듬을 따라 유지 가능한지부터 따져 보는 장면이 자주 나올 수 있습니다."
    )


def _build_year_resource_line(year_pillar: str, year_stem_element: str) -> str:
    return (
        f"소개나 외부 제안이 들어와도 바로 잡기보다 "
        f"{ELEMENT_TONE[year_stem_element]}이 맞는지부터 확인한 뒤 반응하는 편입니다."
    )


def _build_time_resource_line(time_pillar: str, time_branch: str) -> str:
    return (
        f"지출이나 계약을 마감 직전에 다시 볼 때는 {time_branch} 쪽 속도 조절이 작동해, "
        "마지막 확인 절차를 한 번 더 두는 편입니다."
    )


def _strip_day_pillar_prefix(sentence: str, day_kor: str) -> str:
    prefix = f"{day_kor} 일주는 "
    if sentence.startswith(prefix):
        return sentence[len(prefix):].rstrip(".")
    return sentence.rstrip(".")


def _prepend_if_present(options: list[str], preferred: str) -> list[str]:
    if not preferred:
        return options
    return [preferred, *options]


def _clean_options(options: list[str]) -> list[str]:
    return [option for option in options if option]


def _prioritize_section_lines(
    section: dict,
    *,
    easy: list[str],
    real: list[str],
    action: list[str],
    blend_priority: bool = False,
) -> None:
    section["easy_explanation"] = _priority_merge(easy, section["easy_explanation"], blend_priority=blend_priority)
    section["real_life"] = _priority_merge(real, section["real_life"], blend_priority=blend_priority)
    section["action_advice"] = _priority_merge(action, section["action_advice"], blend_priority=blend_priority)
    section["explanation"] = " ".join(section["easy_explanation"])
    section["real_life_text"] = " ".join(section["real_life"])
    section["advice"] = " ".join(section["action_advice"])


def _priority_merge(priority_lines: list[str], current_lines: list[str], *, blend_priority: bool = False) -> list[str]:
    if not priority_lines:
        return current_lines

    merged: list[str] = []
    seen: set[str] = set()
    target_length = len(current_lines)
    if blend_priority:
        max_priority = max(1, (target_length + 1) // 2)
        front_priority = priority_lines[:max_priority]
        tail_priority = priority_lines[max_priority:]
        line_source = [*front_priority, *current_lines, *tail_priority]
    else:
        line_source = [*priority_lines, *current_lines]
    for line in line_source:
        normalized = _to_judgment_tone(line.strip())
        if normalized in seen:
            continue
        merged.append(normalized)
        seen.add(normalized)
        if len(merged) >= target_length:
            break
    return merged


def _pick_profile_line(options: list[str], seed: int) -> str:
    return options[seed % len(options)] if options else ""


def _as_modifier_line(prefix: str, sentence: str) -> str:
    if not sentence:
        return ""
    if sentence.startswith(prefix):
        return sentence
    return f"{prefix}, {sentence[0].lower() + sentence[1:]}" if len(sentence) > 1 else f"{prefix}, {sentence}"


def _current_flow_phrase(year_fortune: dict | None, daewoon: dict | None) -> str:
    if year_fortune and daewoon:
        return (
            f"현재는 세운의 {year_fortune['ten_god']} 기운과 대운의 "
            f"{daewoon['active_cycle_summary']['ten_god']} 기운이 겹쳐 선택과 관리 감각이 더 중요해질 수 있습니다."
        )
    if year_fortune:
        return f"현재는 {year_fortune['ten_god']} 기운이 들어와 {', '.join(year_fortune['focus'][:2])} 쪽 체감이 커질 수 있습니다."
    if daewoon:
        return f"현재 대운에서는 {daewoon['active_cycle_summary']['ten_god']} 기운이 강해 장단점이 더 또렷하게 드러나기 쉽습니다."
    return "현재는 준비된 판단과 생활 리듬을 지키는 태도가 더 큰 차이를 만들 수 있습니다."


def _hidden_group_focus_phrase(group: str | None) -> str:
    mapping = {
        "비겁": "내 기준과 거리 조절",
        "식상": "표현과 실행의 순서",
        "재성": "현실 성과와 관리 기준",
        "관성": "책임과 평가 대응",
        "인성": "해석과 보호 본능",
    }
    return mapping.get(group or "", "안쪽 반응의 결")


def _balance_focus_phrase(yongshin: dict | None) -> str:
    if not yongshin:
        return "우선순위와 처리 범위를 먼저 고정하는"
    mapping = {
        "wood": "막힌 선택지를 조금 열어 두고 조정하는",
        "fire": "말과 행동의 전달 강도를 분명히 다루는",
        "earth": "버틸 수 있는 범위와 현실 조건을 먼저 정하는",
        "metal": "기준과 순서를 먼저 또렷하게 세우는",
        "water": "바로 확정하지 않고 한 번 더 흐름을 살피는",
    }
    return mapping.get(yongshin.get("primary_candidate"), "우선순위와 처리 범위를 먼저 고정하는")


def _balance_support_phrase(yongshin: dict | None) -> str:
    if not yongshin:
        return "세부 기준을 다시 점검하는"
    mapping = {
        "wood": "다음 선택지 하나를 열어 두는",
        "fire": "전달 강도를 한 번 더 다듬는",
        "earth": "무리 없는 범위를 다시 확인하는",
        "metal": "세부 기준을 차분히 정리하는",
        "water": "여지를 조금 남겨 두는",
    }
    return mapping.get(yongshin.get("secondary_candidate"), "세부 기준을 다시 점검하는")


def _balance_reason_lines(yongshin: dict | None) -> list[str]:
    if not yongshin:
        return []
    direction = yongshin.get("direction")
    confidence = yongshin.get("confidence", "medium")
    direction_line = {
        "보강": "지금은 부족한 축을 보강하는 운영이 맞아, 무리한 확장보다 기본 리듬을 먼저 고정하는 편이 좋습니다.",
        "설기·조절": "지금은 힘이 한쪽으로 몰리기 쉬워, 속도보다 강약 조절과 분산 관리가 더 중요합니다.",
        "균형 조정": "지금은 한쪽 해법만 밀기보다 상황에 맞춰 기준을 유연하게 조정하는 편이 안정적입니다.",
    }.get(direction, "지금은 기준을 먼저 세우고 상황에 맞춰 조정하는 운영이 더 안전합니다.")
    confidence_line = {
        "high": "현재 판단 축은 비교적 선명해, 한 번 정한 운영 원칙을 하루 안에서 꾸준히 지키는 편이 유리합니다.",
        "medium": "현재 판단 축은 중간 정도 확신이라, 결론을 빠르게 내리기보다 한 번 더 확인하는 여지를 두는 편이 좋습니다.",
        "low": "현재 판단 축은 변동 여지가 있어, 큰 결정은 단번에 확정하지 말고 단계적으로 나누는 편이 안전합니다.",
    }.get(confidence, "지금은 결론을 한 번에 확정하기보다 확인 단계를 두는 편이 좋습니다.")
    return [direction_line, confidence_line]


def _analysis_overall_openings(
    analysis_context: dict | None,
    current_flow: str,
) -> list[str]:
    if not analysis_context:
        return []
    strength = analysis_context["strength"]["display_label"]
    yongshin = analysis_context["yongshin"]
    balance_focus = _balance_focus_phrase(yongshin)
    structure = analysis_context.get("structure", {})
    primary_pattern = structure.get("primary_pattern", "균형격")
    sub_pattern = structure.get("sub_pattern", "균형 운영형")
    dominant = ", ".join(analysis_context["elements"]["dominant_kor"])
    weak = ", ".join(analysis_context["elements"]["weak_kor"])
    hidden_focus = _hidden_group_focus_phrase(analysis_context["flags"].get("hidden_group_focus"))
    lines = [
        f"핵심 구조는 {primary_pattern}이며 세부 결은 {sub_pattern}으로 읽혀, 같은 일간 안에서도 {balance_focus} 방식에 따라 판단 순서가 꽤 다르게 나타나는 편입니다.",
        f"이 원국은 {strength} 구조이고, 해석의 중심은 {balance_focus} 운영으로 균형을 다시 맞추는 데 있습니다.",
        f"오행 가중치를 함께 보면 {dominant} 기운이 앞서지만, 실제 균형은 {balance_focus} 방향을 살릴 때 더 자연스럽게 잡힙니다.",
        f"겉으로는 {dominant} 기운이 강하고 약한 축은 {weak}이라, 전체 방향은 {balance_focus} 방식으로 보완하는 쪽이 맞습니다.",
        f"안쪽 반응에서는 {hidden_focus}이 먼저 작동해, 겉으로 보이는 성향보다 판단 순서와 균형 회복 방식이 더 중요합니다.",
        current_flow,
    ]
    interactions = analysis_context["interactions"]
    if interactions["natal"]:
        item = interactions["natal"][0]
        lines.append(
            f"원국 안의 {item['target']} {item['type']} 흐름까지 함께 보면, 삶의 방향은 단순 성향보다 상호작용 구조에서 더 크게 갈립니다."
        )
    return lines


def _analysis_personality_openings(analysis_context: dict | None) -> list[str]:
    if not analysis_context:
        return []
    strength = analysis_context["strength"]["display_label"]
    balance_focus = _balance_focus_phrase(analysis_context["yongshin"])
    structure = analysis_context.get("structure", {})
    primary_pattern = structure.get("primary_pattern", "균형격")
    hidden_group = analysis_context["flags"].get("hidden_group_focus")
    hidden_focus = _hidden_group_focus_phrase(hidden_group)
    flags = analysis_context["flags"]
    lines = [
        f"성격 축은 {primary_pattern} 구조의 영향을 크게 받아, 같은 일간이라도 {balance_focus} 방식에 따라 반응 기준이 달라지는 편입니다.",
        f"성격은 {strength} 구조 위에서 {balance_focus} 운영을 하느냐에 따라 장점이 또렷해지는 편입니다.",
        f"겉성격보다 실제 반응은 숨은 십성의 {hidden_focus}이 먼저 작동하는 편이라 판단 순서가 중요합니다.",
        (
            "성격 해석에서는 안쪽 긴장과 바깥 반응이 같이 움직여, 한 번 흔들리면 선택 기준부터 다시 세워야 안정이 잡히는 편입니다."
            if flags["has_natal_conflict"]
            else "성격 해석에서는 강한 충돌보다 안팎의 결이 비교적 이어져, 기준을 세우면 안정적으로 장점을 쓰는 편입니다."
        ),
    ]
    return lines


def _analysis_wealth_openings(
    analysis_context: dict | None,
    year_fortune: dict | None,
    daewoon: dict | None,
) -> list[str]:
    if not analysis_context:
        return []
    strength = analysis_context["strength"]["display_label"]
    balance_focus = _balance_focus_phrase(analysis_context["yongshin"])
    structure = analysis_context.get("structure", {})
    sub_pattern = structure.get("sub_pattern", "균형 운영형")
    weak = ", ".join(analysis_context["elements"]["weak_kor"])
    flow = _current_flow_phrase(year_fortune, daewoon)
    hidden_focus = analysis_context["flags"].get("hidden_group_focus")
    lines = [
        f"재물은 {sub_pattern} 구조의 영향이 커서, {balance_focus} 운영 기준을 어떻게 지키느냐에 따라 벌기보다 보존 규칙에서 결과 차이가 크게 납니다.",
        f"재물은 {strength} 구조를 보완하는 방향을 얼마나 현실 운영으로 연결하느냐에서 차이가 납니다.",
        f"돈 문제는 많이 버는 힘보다 약한 축인 {weak}을 보완할 수 있는 관리 기준이 있느냐가 더 중요합니다.",
        flow,
    ]
    if hidden_focus == "재성":
        lines.append("숨은 십성도 재성 쪽이 먼저 깔려 있어, 수입보다 관리 기준과 생활 운영이 더 직접적으로 결과에 남는 편입니다.")
    elif hidden_focus == "관성":
        lines.append("숨은 십성에 관성 흐름이 깔려 있어, 돈 문제도 책임과 기준을 먼저 세울 때 실제 안정감이 더 커지는 편입니다.")
    elif hidden_focus == "인성":
        lines.append("숨은 십성에 인성 흐름이 깔려 있어, 돈 문제도 바로 쓰기보다 검토와 보완을 먼저 할수록 실수를 줄이는 편입니다.")
    return lines


def _advanced_easy_lines(analysis_context: dict | None, seed: int) -> list[str]:
    if not analysis_context:
        return []
    strength = analysis_context["strength"]
    yongshin = analysis_context["yongshin"]
    balance_focus = _balance_focus_phrase(yongshin)
    support_focus = _balance_support_phrase(yongshin)
    balance_reasons = _balance_reason_lines(yongshin)
    return [
        _pick_profile_line(
            [
                f"중간 계산 기준으로 보면 일간 힘은 {strength['display_label']}으로 읽히고, 중심 기운의 버팀과 소모가 동시에 작동하는 편입니다.",
                f"오행 가중치와 계절 흐름을 함께 보면 현재 원국은 {strength['display_label']} 쪽으로 기울어 해석하는 편이 자연스럽습니다.",
                f"지장간과 계절 보정을 합쳐 보면 원국의 중심 힘은 {strength['display_label']}으로 읽히는 편입니다.",
            ],
            seed,
        ),
        _pick_profile_line(
            [
                f"균형을 맞출 때는 {balance_focus} 쪽 기준을 먼저 세우고, {support_focus} 보조 습관을 함께 두는 편이 좋습니다.",
                f"현재 구조에서는 {balance_focus} 운영을 중심으로 잡고, 세부는 {support_focus} 방식으로 보완하는 편이 무리가 적습니다.",
                f"오늘 판단 순서를 잡을 때는 {balance_focus} 흐름을 먼저 고정한 뒤, {support_focus} 단계로 마무리하는 편이 안정적입니다.",
            ],
            seed + 5,
        ),
        *strength["key_reasons"][:2],
        *balance_reasons[:2],
    ]


def _advanced_real_lines(analysis_context: dict | None, seed: int) -> list[str]:
    if not analysis_context:
        return []
    interactions = analysis_context["interactions"]
    flags = analysis_context["flags"]
    lines: list[str] = []
    if interactions["natal"]:
        natal = interactions["natal"][seed % len(interactions["natal"])]
        lines.append(
            f"같은 문제를 두고 마음과 현실이 다른 쪽으로 끌리는 장면에서는 {natal['meaning']}"
        )
    if interactions["with_daewoon"]:
        daewoon = interactions["with_daewoon"][(seed + 3) % len(interactions["with_daewoon"])]
        lines.append(
            f"역할이 커지거나 환경이 바뀌는 시기에는 {daewoon['meaning']}"
        )
    if interactions["with_yearly"]:
        yearly = interactions["with_yearly"][(seed + 5) % len(interactions["with_yearly"])]
        lines.append(
            f"올해는 일정과 사람 문제가 겹치는 장면에서 {yearly['meaning']}"
        )
    lines.append(
        "여러 장면이 한꺼번에 몰릴 때는 "
        + (
            "선택 충돌과 리듬 차이를 자주 관리해야 하는 편입니다."
            if flags["has_natal_conflict"]
            else "큰 충돌보다 이어지는 결을 살려 장점을 안정적으로 쓰기 쉬운 편입니다."
        )
    )
    return lines


def _advanced_highlight_lines(analysis_context: dict | None) -> list[str]:
    if not analysis_context:
        return []
    strength = analysis_context["strength"]
    yongshin = analysis_context["yongshin"]
    balance_focus = _balance_focus_phrase(yongshin)
    support_focus = _balance_support_phrase(yongshin)
    return [
        f"선택이 몰리는 순간에는 {strength['display_label']} 흐름을 감안해 {balance_focus} 기준을 먼저 세우는 편이 실제 체감 차이를 만들기 쉽습니다.",
        f"문제가 한꺼번에 겹치는 날에는 {support_focus} 운영을 먼저 챙길 때 버티는 힘이 더 안정적으로 남습니다.",
    ]


def _analysis_personality_highlights(analysis_context: dict | None) -> list[str]:
    if not analysis_context:
        return []
    hidden_focus = _hidden_group_focus_phrase(analysis_context["flags"].get("hidden_group_focus"))
    balance_focus = _balance_focus_phrase(analysis_context["yongshin"])
    return [
        f"낯선 사람과 거리를 정해야 하는 장면에서는 {hidden_focus}이 겉반응보다 먼저 올라와 처음 분위기를 주도하는 편입니다.",
        f"결국 사람을 계속 가까이 둘지 선을 그을지는 {balance_focus} 방식으로 균형을 찾는 운영에서 갈리기 쉽습니다.",
    ]


def _analysis_wealth_highlights(
    analysis_context: dict | None,
    year_fortune: dict | None,
    daewoon: dict | None,
) -> list[str]:
    if not analysis_context:
        return []
    if year_fortune and daewoon:
        flow_line = (
            f"이번 시기에는 돈과 역할이 함께 움직이는 장면에서 세운의 {year_fortune['ten_god']} 흐름과 "
            f"대운의 {daewoon['active_cycle_summary']['ten_god']} 흐름이 동시에 판단 속도를 흔들 수 있습니다."
        )
    elif year_fortune:
        flow_line = (
            f"이번 해에는 {', '.join(year_fortune['focus'][:2])} 문제를 같이 챙겨야 하는 장면이 많아져 "
            "돈과 일정 기준을 함께 잡는 편이 훨씬 유리합니다."
        )
    elif daewoon:
        flow_line = (
            f"지금은 {daewoon['active_cycle_summary']['ten_god']} 흐름이 강해져 생활비, 계약, 제안처럼 "
            "현실 판단이 붙는 장면에서 체감 차이가 커지기 쉽습니다."
        )
    else:
        flow_line = "이번 시기에는 돈과 일정이 겹치는 장면에서 먼저 기준을 세우는 편이 흔들림을 줄이기 쉽습니다."
    balance_focus = _balance_focus_phrase(analysis_context["yongshin"])
    return [
        f"돈을 쓸지 말지, 제안을 잡을지 넘길지 정해야 할 때는 {balance_focus} 기준을 먼저 살리는 편이 손실을 줄이기 쉽습니다.",
        flow_line,
    ]


def _pick_strength_risk(
    strength_options: list[str],
    risk_options: list[str],
    count: int,
    state: dict,
    seed: int,
    section_used: set[str],
) -> list[str]:
    picks: list[str] = []
    if strength_options:
        picks.append(_pick_unique(strength_options, seed, state, section_used))
    if risk_options and len(picks) < count:
        picks.append(_pick_unique(risk_options, seed + 7, state, section_used))
    combined = [*strength_options, *risk_options]
    while len(picks) < min(count, len(combined)):
        picks.append(_pick_unique(combined, seed + len(picks) * 11, state, section_used))
    return picks


def _pick_unique(options: list[str], seed: int, state: dict, section_used: set[str]) -> str:
    if not options:
        return ""
    for policy in ("strict", "loose", "fallback"):
        for offset in range(len(options)):
            candidate = options[(seed + offset) % len(options)]
            if candidate in section_used:
                continue
            if policy != "fallback" and candidate in state["sentences"]:
                continue
            if policy == "strict" and _hits_repeat_guard(candidate, state):
                continue
            _remember_sentence(candidate, state, section_used)
            return candidate
    candidate = options[seed % len(options)]
    _remember_sentence(candidate, state, section_used)
    return candidate


def _pick_many(
    options: list[str],
    count: int,
    seed: int,
    state: dict,
    section_used: set[str],
) -> list[str]:
    picks: list[str] = []
    if not options:
        return picks
    target = min(count, len(options))
    for index in range(target):
        picks.append(_pick_unique(options, seed + index * 7, state, section_used))
    return picks


def _rotate_pool(options: list[str], seed: int) -> list[str]:
    if not options:
        return []
    pivot = seed % len(options)
    return options[pivot:] + options[:pivot]


def _section_dict(
    one_line: str,
    highlight: str,
    easy_explanation: list[str],
    real_life: list[str],
    strength_and_risk: list[str],
    action_advice: list[str],
) -> dict:
    return {
        "one_line": one_line,
        "highlight": highlight,
        "easy_explanation": easy_explanation,
        "real_life": real_life,
        "strength_and_risk": strength_and_risk,
        "action_advice": action_advice,
        "headline": one_line,
        "summary": one_line,
        "highlight_text": highlight,
        "explanation": " ".join(easy_explanation),
        "real_life_text": " ".join(real_life),
        "strength_risk_text": " ".join(strength_and_risk),
        "advice": " ".join(action_advice),
    }


def _legacy_list(section: dict) -> list[str]:
    return [
        section["one_line"],
        section["highlight"],
        *section["easy_explanation"],
        *section["real_life"],
        *section["strength_and_risk"],
        *section["action_advice"],
    ]


def _apply_transitions(lines: list[str], seed: int) -> list[str]:
    decorated: list[str] = []
    for index, line in enumerate(lines):
        sentence = _to_judgment_tone(line.strip())
        if index == 0:
            decorated.append(sentence)
            continue
        transition = TRANSITIONS[(seed + index) % len(TRANSITIONS)]
        decorated.append(f"{transition}, {sentence[0].lower() + sentence[1:]}" if len(sentence) > 1 else f"{transition}, {sentence}")
    return decorated


def _build_highlight(
    highlight_options: list[str],
    *,
    one_line: str,
    easy_explanation: list[str],
    real_life: list[str],
    strength_and_risk: list[str],
    action_advice: list[str],
    seed: int,
) -> str:
    preferred_candidates = [
        *real_life[:2],
        one_line,
        *action_advice[:2],
        *highlight_options[:2],
        *easy_explanation[:1],
    ]
    support_candidates = [
        *highlight_options[2:],
        *easy_explanation[1:],
        *real_life[2:],
        *action_advice[2:],
        *strength_and_risk,
    ]
    candidates = preferred_candidates or support_candidates
    if not candidates:
        candidates = support_candidates
    if not candidates:
        return ""
    opener = HIGHLIGHT_OPENERS[seed % len(HIGHLIGHT_OPENERS)]
    base = _strip_transition_prefix(candidates[seed % len(candidates)])
    highlighted = _to_judgment_tone(base)
    if not highlighted.endswith("."):
        highlighted = f"{highlighted}."
    return f"{opener}, {highlighted}"


def _strip_transition_prefix(sentence: str) -> str:
    stripped = sentence.strip()
    for transition in sorted(TRANSITIONS, key=len, reverse=True):
        prefix = f"{transition}, "
        if stripped.startswith(prefix):
            return stripped[len(prefix):]
    return stripped


def _to_judgment_tone(sentence: str) -> str:
    replacements = (
        ("기 좋은 쪽으로 읽는 편이 맞습니다.", "기 좋은 흐름입니다."),
        ("기 좋은 날로 보는 쪽이 맞습니다.", "기 좋은 날입니다."),
        ("중요하게 보는 쪽이 더 맞습니다.", "중요합니다."),
        ("유리한 쪽으로 보는 편이 맞습니다.", "유리합니다."),
        ("좋은 편으로 보는 쪽이 맞습니다.", "좋습니다."),
        ("편으로 읽는 쪽이 더 맞습니다.", "편입니다."),
        ("구조로 보는 쪽이 더 맞습니다.", "구조입니다."),
        ("흐름으로 읽는 쪽이 더 맞습니다.", "흐름입니다."),
        ("시기로 보는 쪽이 더 맞습니다.", "시기입니다."),
        ("날로 보는 쪽이 더 맞습니다.", "날입니다."),
        ("라는 해석이 더 맞습니다.", "입니다."),
    )
    for source, target in replacements:
        sentence = sentence.replace(source, target)
    return sentence


def build_yearly_section(
    *,
    headline: str,
    explanation: str,
    advice: str,
    focus: list[str],
    seed: int,
    used_sentences: dict | set[str] | None = None,
) -> dict:
    """Build a structured yearly section."""
    real_life_lines = [
        *_rotate_pool(FORTUNE_REAL_LIFE, seed + 5),
        *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 11),
    ]
    easy_lines = [headline, explanation, *_rotate_pool(FORTUNE_EXPLAIN, seed + 17)]
    action_lines = [advice, *_rotate_pool(FORTUNE_ACTION, seed + 23)]
    one_line_options = [headline, *_rotate_pool(FORTUNE_SUMMARY, seed + 29)]
    if focus:
        easy_lines.append(f"올해는 {', '.join(focus[:2])} 문제가 실제 일정과 판단에서 더 자주 체감될 수 있습니다.")
        real_life_lines.insert(0, f"현실에서는 {', '.join(focus[:2])}을 먼저 챙겨야 하는 상황이 반복될 가능성이 있습니다.")
    return create_flow_section(
        one_line_seed_options=one_line_options,
        extra_easy_lines=easy_lines,
        extra_real_life_lines=real_life_lines,
        extra_action_lines=action_lines,
        strength_options=_rotate_pool(STRENGTH_TEMPLATES, seed + 31),
        risk_options=_rotate_pool(RISK_TEMPLATES, seed + 37),
        highlight_options=[headline, explanation, *_rotate_pool(FORTUNE_SUMMARY, seed + 41)],
        seed=seed,
        used_sentences=used_sentences,
        easy_count=2,
        real_life_count=3,
    )


def build_daily_section(
    *,
    headline: str,
    explanation: str,
    advice: str,
    keywords: list[str],
    seed: int,
    used_sentences: dict | set[str] | None = None,
    context_easy_lines: list[str] | None = None,
    context_real_lines: list[str] | None = None,
    context_action_lines: list[str] | None = None,
    strength_lines: list[str] | None = None,
    risk_lines: list[str] | None = None,
) -> dict:
    """Build a structured daily section."""
    easy_lines = [headline, explanation, *(context_easy_lines or []), *_rotate_pool(DAILY_EXPLAIN, seed + 5)]
    real_lines = [
        *(context_real_lines or []),
        *_rotate_pool(DAILY_REAL_LIFE, seed + 9),
        *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 13),
    ]
    if keywords:
        real_lines.insert(0, f"오늘은 {', '.join(keywords[:2])} 같은 키워드가 실제 일정과 판단에 바로 연결될 수 있습니다.")
    action_lines = [advice, *(context_action_lines or []), *_rotate_pool(DAILY_ACTION, seed + 17)]
    section = create_flow_section(
        one_line_seed_options=[headline, *_rotate_pool(DAILY_SUMMARY, seed)],
        extra_easy_lines=easy_lines,
        extra_real_life_lines=real_lines,
        extra_action_lines=action_lines,
        strength_options=[*(strength_lines or [])] or _rotate_pool(STRENGTH_TEMPLATES, seed + 19),
        risk_options=[*(risk_lines or [])] or _rotate_pool(RISK_TEMPLATES, seed + 23),
        highlight_options=[headline, advice, *(strength_lines or []), *(risk_lines or []), *_rotate_pool(DAILY_SUMMARY, seed + 29)],
        seed=seed,
        used_sentences=used_sentences,
        easy_count=5,
        real_life_count=6,
        action_count=3,
        strength_risk_count=5,
    )
    _prioritize_section_lines(
        section,
        easy=context_easy_lines or [],
        real=context_real_lines or [],
        action=context_action_lines or [],
        blend_priority=True,
    )
    section["one_line"] = headline
    section["headline"] = headline
    section["summary"] = headline
    return section


def build_career_section(
    *,
    headline: str,
    explanation: str,
    advice: str,
    strengths: list[str],
    warnings: list[str],
    seed: int,
    used_sentences: dict | set[str] | None = None,
    context_easy_lines: list[str] | None = None,
    context_real_lines: list[str] | None = None,
    context_action_lines: list[str] | None = None,
) -> dict:
    """Build a structured career section."""
    section = create_flow_section(
        one_line_seed_options=[headline, *_rotate_pool(CAREER_SUMMARY, seed)],
        extra_easy_lines=[explanation, *(context_easy_lines or []), *_rotate_pool(WORK_STYLE_TEMPLATES, seed + 5)],
        extra_real_life_lines=[
            *(context_real_lines or []),
            *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 11),
            *strengths,
            *_rotate_pool(CAREER_REAL_LIFE, seed + 17),
        ],
        extra_action_lines=[advice, *(context_action_lines or []), *_rotate_pool(CAREER_ACTION, seed + 23)],
        strength_options=[*strengths, *_rotate_pool(STRENGTH_TEMPLATES, seed + 29)],
        risk_options=[*warnings, *_rotate_pool(RISK_TEMPLATES, seed + 31)],
        highlight_options=[headline, *strengths, advice],
        seed=seed,
        used_sentences=used_sentences,
        easy_count=5,
        real_life_count=6,
        action_count=3,
        strength_risk_count=5,
    )
    _prioritize_section_lines(
        section,
        easy=context_easy_lines or [],
        real=context_real_lines or [],
        action=context_action_lines or [],
        blend_priority=True,
    )
    section["one_line"] = headline
    section["headline"] = headline
    section["summary"] = headline
    return section


def build_relationship_section(
    *,
    headline: str,
    explanation: str,
    advice: str,
    strengths: list[str],
    warnings: list[str],
    seed: int,
    used_sentences: dict | set[str] | None = None,
    context_easy_lines: list[str] | None = None,
    context_real_lines: list[str] | None = None,
    context_action_lines: list[str] | None = None,
) -> dict:
    """Build a structured relationship section."""
    section = create_flow_section(
        one_line_seed_options=[headline, *_rotate_pool(RELATIONSHIP_SUMMARY, seed)],
        extra_easy_lines=[explanation, *(context_easy_lines or []), *_rotate_pool(SOCIAL_TEMPLATES, seed + 5)],
        extra_real_life_lines=[
            *(context_real_lines or []),
            *_rotate_pool(RELATIONSHIP_REAL_LIFE, seed + 11),
            *_rotate_pool(RELATIONSHIP_SPEED_TEMPLATES, seed + 17),
            *_rotate_pool(SPEECH_TEMPLATES, seed + 23),
        ],
        extra_action_lines=[advice, *(context_action_lines or []), *_rotate_pool(RELATIONSHIP_ACTION, seed + 29)],
        strength_options=[*strengths, *_rotate_pool(STRENGTH_TEMPLATES, seed + 31)],
        risk_options=[*warnings, *_rotate_pool(RISK_TEMPLATES, seed + 37)],
        highlight_options=[headline, *strengths, advice],
        seed=seed,
        used_sentences=used_sentences,
        easy_count=5,
        real_life_count=6,
        action_count=3,
        strength_risk_count=5,
    )
    _prioritize_section_lines(
        section,
        easy=context_easy_lines or [],
        real=context_real_lines or [],
        action=context_action_lines or [],
        blend_priority=True,
    )
    section["one_line"] = headline
    section["headline"] = headline
    section["summary"] = headline
    return section


def build_active_daewoon_section(
    *,
    headline: str,
    explanation: str,
    advice: str,
    keywords: list[str],
    seed: int,
    used_sentences: dict | set[str] | None = None,
) -> dict:
    """Build a structured active daewoon section."""
    real_lines = [*_rotate_pool(FORTUNE_REAL_LIFE, seed + 7), *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 13)]
    if keywords:
        real_lines.insert(0, f"현실에서는 {', '.join(keywords[:2])} 같은 주제가 반복해서 체감될 가능성이 높습니다.")
    return create_flow_section(
        one_line_seed_options=[headline, *_rotate_pool(FORTUNE_SUMMARY, seed)],
        extra_easy_lines=[explanation, *_rotate_pool(FORTUNE_EXPLAIN, seed + 3)],
        extra_real_life_lines=real_lines,
        extra_action_lines=[advice, *_rotate_pool(FORTUNE_ACTION, seed + 19)],
        strength_options=_rotate_pool(STRENGTH_TEMPLATES, seed + 23),
        risk_options=_rotate_pool(RISK_TEMPLATES, seed + 29),
        highlight_options=[headline, explanation, advice],
        seed=seed,
        used_sentences=used_sentences,
        easy_count=2,
        real_life_count=3,
    )


def _create_state() -> dict:
    return {"sentences": set(), "keyword_hits": Counter()}


def _ensure_state(used_sentences: dict | set[str] | None) -> dict:
    if used_sentences is None:
        return _create_state()
    if isinstance(used_sentences, dict):
        used_sentences.setdefault("sentences", set())
        used_sentences.setdefault("keyword_hits", Counter())
        return used_sentences
    return {"sentences": used_sentences, "keyword_hits": Counter()}


def _hits_repeat_guard(sentence: str, state: dict) -> bool:
    return any(state["keyword_hits"][word] >= 2 for word in REPEAT_GUARD_WORDS if word in sentence)


def _remember_sentence(sentence: str, state: dict, section_used: set[str]) -> None:
    section_used.add(sentence)
    state["sentences"].add(sentence)
    for word in REPEAT_GUARD_WORDS:
        if word in sentence:
            state["keyword_hits"][word] += 1
