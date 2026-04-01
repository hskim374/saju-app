"""Narrative interpretation engine with five-step report sections."""

from __future__ import annotations

from collections import Counter

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


def build_interpretation_payload(
    *,
    element_analysis: dict,
    ten_gods: dict | None = None,
    daewoon: dict | None = None,
    year_fortune: dict | None = None,
) -> dict:
    """Build story-like sections for the natal chart."""
    page_state = _create_state()
    seed = build_seed(
        element_analysis["dominant"],
        element_analysis["weak"],
        element_analysis["elements"],
        year_fortune["pillar"] if year_fortune else "",
    )
    overall = _build_overall_section(element_analysis, ten_gods, daewoon, year_fortune, seed, page_state)
    personality = _build_personality_section(element_analysis, seed + 11, page_state)
    wealth = _build_wealth_section(element_analysis, seed + 23, page_state)
    return {
        "summary": overall["one_line"],
        "personality": _legacy_list(personality),
        "wealth": _legacy_list(wealth),
        "interpretation_sections": {
            "overall": overall,
            "personality": personality,
            "wealth": wealth,
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
        strength_risk_count=2,
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
    seed: int,
    state: dict,
) -> dict:
    dominant = element_analysis["dominant"]
    weak = element_analysis["weak"]
    support = pick_support_elements(element_analysis)
    month_star = ten_gods["ten_gods"].get("month") if ten_gods else None
    current_flow = _current_flow_phrase(year_fortune, daewoon)

    easy_options = [dominant_story(dominant, seed)]
    for index, element in enumerate(dominant[:2]):
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[element], seed + index * 5))
    if support:
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[support[0]], seed + 13))
    if weak:
        easy_options.extend(_rotate_pool(ELEMENT_WEAK_TEMPLATES[weak[0]], seed + 19))
    if month_star:
        easy_options.append(select_ten_god_explanation(month_star, seed + 23))
    easy_options.append(current_flow)

    real_life_options = [
        *_rotate_pool(DECISION_TEMPLATES, seed + 29),
        *_rotate_pool(SOCIAL_TEMPLATES, seed + 37),
        *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 41),
        *_rotate_pool(PERSONALITY_REAL_LIFE, seed + 47),
    ]

    one_line_options = [
        f"{join_elements(dominant)} 기운이 중심이 되어 삶의 판단과 반응 방향을 이끄는 구조입니다.",
        f"{join_elements(dominant)} 기운이 앞에 서서 생활 전반의 선택 기준을 주도하는 편입니다.",
        f"{join_elements(dominant)} 기운이 선명해 일상에서 드러나는 성향의 결이 비교적 분명합니다.",
        f"{join_elements(dominant)} 기운이 주도권을 잡아 쉽게 흔들리기보다 오래 보는 판단이 먼저 들어갑니다.",
        f"{join_elements(dominant)} 기운이 중심축이 되어 생각과 행동이 한쪽으로 모이기 쉬운 편입니다.",
    ]
    return build_report_section(
        one_line_options=one_line_options,
        easy_explanation_options=easy_options,
        real_life_options=real_life_options,
        action_advice_options=_rotate_pool(PERSONALITY_ACTION, seed + 53),
        strength_options=_rotate_pool(STRENGTH_TEMPLATES, seed + 59),
        risk_options=_rotate_pool(RISK_TEMPLATES, seed + 67),
        highlight_options=[
            current_flow,
            dominant_story(dominant, seed + 71),
            *_rotate_pool(STRENGTH_TEMPLATES, seed + 73),
        ],
        seed=seed,
        used_sentences=state,
        easy_count=3,
        real_life_count=3,
    )


def _build_personality_section(element_analysis: dict, seed: int, state: dict) -> dict:
    dominant = element_analysis["dominant"]
    weak = element_analysis["weak"]
    support = pick_support_elements(element_analysis)
    easy_options = []
    for index, element in enumerate(dominant[:2]):
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[element], seed + index * 5))
    if support:
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[support[0]], seed + 17))
    if weak:
        easy_options.extend(_rotate_pool(ELEMENT_WEAK_TEMPLATES[weak[0]], seed + 23))
    easy_options.append(dominant_story(dominant, seed + 29))

    real_life_options = [
        *_rotate_pool(SOCIAL_TEMPLATES, seed + 31),
        *_rotate_pool(STRESS_TEMPLATES, seed + 37),
        *_rotate_pool(DECISION_TEMPLATES, seed + 43),
        *_rotate_pool(PERSONALITY_REAL_LIFE, seed + 47),
    ]

    return build_report_section(
        one_line_options=_rotate_pool(PERSONALITY_SUMMARY, seed),
        easy_explanation_options=easy_options,
        real_life_options=real_life_options,
        action_advice_options=_rotate_pool(PERSONALITY_ACTION, seed + 53),
        strength_options=_rotate_pool(STRENGTH_TEMPLATES, seed + 59),
        risk_options=_rotate_pool(RISK_TEMPLATES, seed + 67),
        highlight_options=[
            *_rotate_pool(STRENGTH_TEMPLATES, seed + 71),
            *_rotate_pool(DECISION_TEMPLATES, seed + 79),
        ],
        seed=seed,
        used_sentences=state,
        easy_count=3,
        real_life_count=3,
    )


def _build_wealth_section(element_analysis: dict, seed: int, state: dict) -> dict:
    dominant = element_analysis["dominant"]
    weak = element_analysis["weak"]
    easy_options = [dominant_story(dominant, seed + 3)]
    for index, element in enumerate(dominant[:2]):
        easy_options.extend(_rotate_pool(ELEMENT_STRONG_TEMPLATES[element], seed + index * 7))
    if weak:
        easy_options.extend(_rotate_pool(ELEMENT_WEAK_TEMPLATES[weak[0]], seed + 17))

    real_life_options = [
        *_rotate_pool(MONEY_REAL_LIFE, seed + 23),
        *_rotate_pool(MONEY_HABIT_TEMPLATES, seed + 29),
        *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 37),
    ]

    return build_report_section(
        one_line_options=_rotate_pool(MONEY_SUMMARY, seed),
        easy_explanation_options=easy_options,
        real_life_options=real_life_options,
        action_advice_options=_rotate_pool(MONEY_ACTION, seed + 43),
        strength_options=_rotate_pool(STRENGTH_TEMPLATES, seed + 47),
        risk_options=_rotate_pool(RISK_TEMPLATES, seed + 53),
        highlight_options=[
            *_rotate_pool(MONEY_HABIT_TEMPLATES, seed + 59),
            *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 67),
        ],
        seed=seed,
        used_sentences=state,
        easy_count=2,
        real_life_count=3,
    )


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
    candidates = [
        *highlight_options,
        *strength_and_risk,
        *action_advice,
        *real_life,
        *easy_explanation,
        one_line,
    ]
    if not candidates:
        return ""
    opener = HIGHLIGHT_OPENERS[seed % len(HIGHLIGHT_OPENERS)]
    base = candidates[seed % len(candidates)]
    highlighted = _to_judgment_tone(base)
    if not highlighted.endswith("."):
        highlighted = f"{highlighted}."
    return f"{opener}, {highlighted}"


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
) -> dict:
    """Build a structured daily section."""
    easy_lines = [headline, explanation, *_rotate_pool(DAILY_EXPLAIN, seed + 5)]
    real_lines = [*_rotate_pool(DAILY_REAL_LIFE, seed + 9), *_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 13)]
    if keywords:
        real_lines.insert(0, f"오늘은 {', '.join(keywords[:2])} 같은 키워드가 실제 일정과 판단에 바로 연결될 수 있습니다.")
    action_lines = [advice, *_rotate_pool(DAILY_ACTION, seed + 17)]
    return create_flow_section(
        one_line_seed_options=[headline, *_rotate_pool(DAILY_SUMMARY, seed)],
        extra_easy_lines=easy_lines,
        extra_real_life_lines=real_lines,
        extra_action_lines=action_lines,
        strength_options=_rotate_pool(STRENGTH_TEMPLATES, seed + 19),
        risk_options=_rotate_pool(RISK_TEMPLATES, seed + 23),
        highlight_options=[headline, advice, *_rotate_pool(DAILY_SUMMARY, seed + 29)],
        seed=seed,
        used_sentences=used_sentences,
        easy_count=2,
        real_life_count=3,
    )


def build_career_section(
    *,
    headline: str,
    explanation: str,
    advice: str,
    strengths: list[str],
    warnings: list[str],
    seed: int,
    used_sentences: dict | set[str] | None = None,
) -> dict:
    """Build a structured career section."""
    return create_flow_section(
        one_line_seed_options=[headline, *_rotate_pool(CAREER_SUMMARY, seed)],
        extra_easy_lines=[explanation, *_rotate_pool(WORK_STYLE_TEMPLATES, seed + 5)],
        extra_real_life_lines=[*_rotate_pool(OPPORTUNITY_TEMPLATES, seed + 11), *strengths, *_rotate_pool(CAREER_REAL_LIFE, seed + 17)],
        extra_action_lines=[advice, *_rotate_pool(CAREER_ACTION, seed + 23)],
        strength_options=[*strengths, *_rotate_pool(STRENGTH_TEMPLATES, seed + 29)],
        risk_options=[*warnings, *_rotate_pool(RISK_TEMPLATES, seed + 31)],
        highlight_options=[headline, *strengths, advice],
        seed=seed,
        used_sentences=used_sentences,
        easy_count=2,
        real_life_count=3,
    )


def build_relationship_section(
    *,
    headline: str,
    explanation: str,
    advice: str,
    strengths: list[str],
    warnings: list[str],
    seed: int,
    used_sentences: dict | set[str] | None = None,
) -> dict:
    """Build a structured relationship section."""
    return create_flow_section(
        one_line_seed_options=[headline, *_rotate_pool(RELATIONSHIP_SUMMARY, seed)],
        extra_easy_lines=[explanation, *_rotate_pool(SOCIAL_TEMPLATES, seed + 5)],
        extra_real_life_lines=[*_rotate_pool(RELATIONSHIP_REAL_LIFE, seed + 11), *_rotate_pool(RELATIONSHIP_SPEED_TEMPLATES, seed + 17), *_rotate_pool(SPEECH_TEMPLATES, seed + 23)],
        extra_action_lines=[advice, *_rotate_pool(RELATIONSHIP_ACTION, seed + 29)],
        strength_options=[*strengths, *_rotate_pool(STRENGTH_TEMPLATES, seed + 31)],
        risk_options=[*warnings, *_rotate_pool(RISK_TEMPLATES, seed + 37)],
        highlight_options=[headline, *strengths, advice],
        seed=seed,
        used_sentences=used_sentences,
        easy_count=2,
        real_life_count=3,
    )


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
