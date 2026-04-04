"""Relationship and marriage fortune interpretation."""

from __future__ import annotations

from data.day_pillar_sentences import DAY_PILLAR_SENTENCES
from data.month_ten_god_specialized import MONTH_TEN_GOD_RELATION_LINES
from services.analysis_sentence_store import load_analysis_sentences
from services.interpretation_engine import build_relationship_section
from services.ten_gods import calculate_ten_gods

RELATIONSHIP_RULES = {
    "wealth": {
        "trend": "인연 유입",
        "strong": "인연운이 강하게 들어오지만 속도보다 안정성을 먼저 확인해야 하는 흐름입니다.",
        "medium": "사람 흐름이 열리되 감정과 현실 조건을 함께 보는 편이 좋은 흐름입니다.",
        "light": "관계의 문이 조금씩 열리므로 자연스러운 접점을 넓히는 편이 좋습니다.",
        "strengths": [
            "새로운 만남이나 관계로 이어질 외부 접점이 늘어날 수 있습니다.",
            "호감이 생기더라도 현실 조건을 같이 보는 태도가 오히려 관계를 안정시킵니다.",
        ],
        "warnings": [
            "감정이 앞서면 속도가 빨라질 수 있어 결정은 한 박자 늦추는 편이 좋습니다.",
        ],
    },
    "officer": {
        "trend": "안정/판단",
        "strong": "관계의 방향이 또렷해지지만 기준을 분명히 세워야 흐름이 살아나는 시기입니다.",
        "medium": "인연보다 관계의 안정성과 책임감이 더 중요해지는 흐름입니다.",
        "light": "천천히 관계의 기준을 정리하면 흐름이 부드럽게 이어질 수 있습니다.",
        "strengths": [
            "책임감 있는 인연이나 관계 정리가 눈에 들어오기 쉬운 시기입니다.",
            "관계의 기준을 분명히 할수록 안정성이 높아집니다.",
        ],
        "warnings": [
            "상대의 속도보다 자신의 판단 기준을 먼저 확인하는 편이 좋습니다.",
        ],
    },
    "mixed": {
        "trend": "재정비",
        "strong": "관계는 유지보다 재정비 흐름이 강해 감정의 속도와 거리 조절이 핵심이 됩니다.",
        "medium": "새 인연보다 소통 방식과 거리 조절을 손보는 쪽에 무게가 실립니다.",
        "light": "관계 흐름은 서서히 움직이므로 대화의 톤을 정리하는 편이 좋습니다.",
        "strengths": [
            "대화 방식과 거리 조절을 정리하면 관계 흐름이 한결 부드러워질 수 있습니다.",
        ],
        "warnings": [
            "감정 기복이 큰 날에는 결론을 서두르지 않는 편이 안전합니다.",
        ],
    },
}

DAY_STEM_RELATION_LINES = {
    "갑": "원국 일간이 갑목이면 관계에서도 방향과 태도가 맞는지를 먼저 보며 쉽게 타협하지 않는 편입니다.",
    "을": "원국 일간이 을목이면 관계에서는 부드럽게 맞추지만 속으로는 리듬과 안전선을 오래 보는 편입니다.",
    "병": "원국 일간이 병화이면 호감이 생겼을 때 표현과 반응이 빠르게 밖으로 드러나기 쉬운 편입니다.",
    "정": "원국 일간이 정화이면 관계에서도 분위기와 타이밍을 먼저 보고 감정을 조심스럽게 꺼내는 편입니다.",
    "무": "원국 일간이 무토이면 관계에서도 감정 자체보다 오래 갈 수 있는지와 현실성을 먼저 따지는 편입니다.",
    "기": "원국 일간이 기토이면 상대 상황과 내 현실을 같이 보며 무리 없는 속도로 맞추려는 편입니다.",
    "경": "원국 일간이 경금이면 관계에서도 애매한 상태를 오래 두기보다 기준과 선을 분명히 하고 싶은 편입니다.",
    "신": "원국 일간이 신금이면 표현은 절제되어도 세부적인 태도와 균형을 꽤 오래 보는 편입니다.",
    "임": "원국 일간이 임수이면 관계에서도 감정 하나보다 전체 흐름과 가능성을 넓게 읽는 쪽으로 움직입니다.",
    "계": "원국 일간이 계수이면 관계에서는 겉표현보다 분위기와 맥락을 더 오래 읽으며 판단하는 편입니다.",
}

MONTH_BRANCH_RELATION_LINES = {
    "자": "월지가 자수라 관계에서도 먼저 흐름과 분위기를 읽어야 마음이 놓이는 편입니다.",
    "축": "월지가 축토라 관계에서는 천천히 쌓이는 신뢰와 버틸 수 있는 생활 감각을 더 중요하게 봅니다.",
    "인": "월지가 인목이라 관계도 정체된 상태보다 앞으로 나아가는 느낌이 있어야 힘이 붙기 쉽습니다.",
    "묘": "월지가 묘목이라 감정의 세기보다 관계 리듬과 거리 조절의 부드러움이 더 중요하게 작동합니다.",
    "진": "월지가 진토라 관계에서도 여러 조건을 같이 보고 현실적으로 맞는지를 따지는 편입니다.",
    "사": "월지가 사화라 관계에서 반응 속도가 빨라질 수 있어 감정이 달아오를 때 페이스 조절이 중요합니다.",
    "오": "월지가 오화라 관계에서도 정적인 흐름보다 살아 있는 반응과 존재감이 보일 때 끌리기 쉽습니다.",
    "미": "월지가 미토라 관계에서는 겉으로 빠르지 않아도 오래 갈 수 있는 안정감이 더 중요합니다.",
    "신": "월지가 신금이라 관계에서도 말보다 태도, 약속, 선 긋기 같은 기준을 더 민감하게 보는 편입니다.",
    "유": "월지가 유금이라 가까워질수록 세부 태도와 완성도를 보며 관계 판단을 더 섬세하게 하는 편입니다.",
    "술": "월지가 술토라 관계에서도 책임감과 일관성이 확인될 때 비로소 마음을 더 여는 편입니다.",
    "해": "월지가 해수라 관계는 서두르기보다 여지를 두고 천천히 보는 쪽이 더 자연스럽습니다.",
}

TIME_BRANCH_RELATION_LINES = {
    "자": "시지에 자수가 놓이면 가까운 관계일수록 속으로 생각이 길어져 결론을 늦추는 편입니다.",
    "축": "시지에 축토가 놓이면 친밀한 관계에서도 급히 열기보다 안에서 정리한 뒤 표현하는 편입니다.",
    "인": "시지에 인목이 놓이면 시간이 갈수록 관계에서 더 넓은 가능성과 방향을 보고 싶어질 수 있습니다.",
    "묘": "시지에 묘목이 놓이면 가까운 관계일수록 거리 조절과 부드러운 호흡이 중요하게 작동합니다.",
    "진": "시지에 진토가 놓이면 친한 사이일수록 여러 조건을 현실적으로 비교하며 쉽게 확정하지 않는 편입니다.",
    "사": "시지에 사화가 놓이면 가까운 사람 앞에서는 표현과 반응이 더 빨라질 수 있습니다.",
    "오": "시지에 오화가 놓이면 친밀한 관계에서 감정이 붙었을 때 속도와 열기가 크게 올라오기 쉽습니다.",
    "미": "시지에 미토가 놓이면 시간이 갈수록 관계에서도 오래 갈 수 있는 안정감을 더 중요하게 봅니다.",
    "신": "시지에 신금이 놓이면 가까운 관계일수록 선과 기준을 더 분명히 하고 싶어지는 편입니다.",
    "유": "시지에 유금이 놓이면 친밀한 사이에서도 사소한 태도 차이를 오래 기억하는 편입니다.",
    "술": "시지에 술토가 놓이면 가까운 관계일수록 책임감과 신뢰 문제를 더 무겁게 보는 편입니다.",
    "해": "시지에 해수가 놓이면 친밀한 관계에서는 결론보다 여지를 남겨 두는 태도가 먼저 나올 수 있습니다.",
}

RELATIONSHIP_SPEED_WARNINGS = {
    "사": "감정이 붙었을 때 속도가 빨라질 수 있어 결정은 하루 정도 늦추는 편이 좋습니다.",
    "오": "관계 열기가 올라올수록 말의 수위와 연락 빈도를 같이 조절하는 편이 안정적입니다.",
    "자": "생각이 길어질수록 타이밍이 늦어질 수 있어 기준을 먼저 정리하는 편이 좋습니다.",
    "해": "여지를 오래 두는 성향이 강해지면 상대에게 애매하게 보일 수 있어 표현 시점을 잡는 편이 좋습니다.",
}

RELATIONSHIP_PROFILE_HEADLINES = {
    "slow_trust": "관계는 빠른 감정보다 천천히 쌓이는 신뢰에서 차이가 나는 타입입니다.",
    "pace_adjuster": "관계는 감정 크기보다 속도와 거리 조절에서 결과가 갈리는 타입입니다.",
    "boundary_first": "관계는 호감보다 기준과 선이 분명해야 편안해지는 타입입니다.",
    "observer": "관계는 표현보다 관찰과 맥락 읽기가 먼저 작동하는 타입입니다.",
    "expressive": "관계는 마음이 움직이면 반응과 표현이 빨라지기 쉬운 타입입니다.",
    "balanced_connector": "관계는 상대와의 호흡을 맞추며 조율하는 장점이 큰 타입입니다.",
}

RELATIONSHIP_PROFILE_SUMMARIES = {
    "slow_trust": "좋아도 바로 깊게 들어가기보다 시간이 지나며 신뢰가 쌓일 때 관계가 안정되기 쉽습니다.",
    "pace_adjuster": "관계가 틀어지는 이유도 감정보다 속도 차이에서 시작될 가능성이 큽니다.",
    "boundary_first": "애매한 상태를 오래 두기보다 선과 기준이 정리될 때 마음이 더 편해지기 쉽습니다.",
    "observer": "호감이 있어도 먼저 분위기와 흐름을 읽으며 타이밍을 보는 쪽으로 움직일 가능성이 큽니다.",
    "expressive": "감정이 붙을 때 속도와 열기가 함께 올라오기 쉬워 호흡 조절이 중요합니다.",
    "balanced_connector": "서로의 리듬을 맞추는 힘은 좋지만, 내 속도를 잃지 않는 기준도 같이 필요합니다.",
}

RELATIONSHIP_PROFILE_ADVICE = {
    "slow_trust": "좋아도 빠르게 확정하지 말고 서로의 생활 리듬이 맞는지 먼저 보는 편이 좋습니다.",
    "pace_adjuster": "감정이 커질수록 연락 빈도와 가까워지는 속도를 의식적으로 늦추는 편이 좋습니다.",
    "boundary_first": "상대에게 맞추기 전에 내가 편한 거리와 기준을 먼저 설명하는 편이 더 안정적입니다.",
    "observer": "계속 관찰만 하기보다 표현 시점을 하나 정해 두는 편이 관계 흐름을 놓치지 않는 데 도움이 됩니다.",
    "expressive": "호감이 커질수록 결론을 하루 정도 늦추고 말의 강약을 조절하는 편이 좋습니다.",
    "balanced_connector": "상대에게 맞추는 장점을 살리되 내 리듬을 지키는 기준을 같이 두는 편이 좋습니다.",
}


def build_relationship_fortune(gender: str, year_fortune: dict, saju_result: dict | None = None) -> dict:
    """Build a relationship fortune from natal chart, gender, and yearly flow."""
    current_stars = [year_fortune["ten_god"], year_fortune["daewoon_ten_god"]]
    current_star_set = set(current_stars)

    if gender == "male":
        relevant_stars = {"편재", "정재"}
        profile = "wealth"
    elif gender == "female":
        relevant_stars = {"편관", "정관"}
        profile = "officer"
    else:
        relevant_stars = {"편재", "정재", "편관", "정관"}
        profile = "mixed"

    strength_profile = profile if current_star_set & relevant_stars else "mixed"
    intensity = _resolve_intensity(current_stars, strength_profile)
    rule = RELATIONSHIP_RULES[strength_profile]
    strengths = list(rule["strengths"])
    warnings = list(rule["warnings"])
    relationship_profile = "balanced_connector"

    context_easy_lines: list[str] = []
    context_real_lines: list[str] = []
    context_action_lines: list[str] = []

    if saju_result:
        saju = saju_result["saju"]
        day_stem = saju["day"]["stem"]
        day_pillar_kor = saju["day"]["kor"]
        month_branch = saju["month"]["branch"]
        time_branch = saju["time"]["branch"] if saju.get("time") else None
        ten_gods = calculate_ten_gods(saju)
        month_ten_god = ten_gods["ten_gods"]["month"]
        day_pillar_line = DAY_PILLAR_SENTENCES[day_pillar_kor]["relationship"]
        sentence_data = load_analysis_sentences()
        day_data = sentence_data["day_stem"][day_stem]
        month_data = sentence_data["month_branch"][month_branch]
        time_data = sentence_data["time_branch"].get(time_branch) if time_branch else None
        month_ten_god_data = sentence_data["month_ten_god"].get(month_ten_god) if month_ten_god else None
        seed = len("".join(current_stars)) + len(strength_profile) + len(day_stem) + len(month_branch)
        relationship_profile = _resolve_relationship_profile(day_stem, month_branch, time_branch)
        month_ten_god_relation_line = (
            _pick(MONTH_TEN_GOD_RELATION_LINES[month_ten_god], seed + 2)
            if month_ten_god
            else ""
        )

        context_easy_lines = [
            day_pillar_line,
            month_ten_god_relation_line,
            RELATIONSHIP_PROFILE_HEADLINES[relationship_profile],
            DAY_STEM_RELATION_LINES[day_stem],
            MONTH_BRANCH_RELATION_LINES[month_branch],
            _pick(day_data["social_reaction"], seed + 3),
        ]
        if month_ten_god_data:
            context_easy_lines.append(
                f"월간 십성 보정으로 보면 {_pick(month_ten_god_data['personality_modifier'], seed + 5).lower()}"
            )
        if time_branch:
            context_easy_lines.append(TIME_BRANCH_RELATION_LINES[time_branch])

        context_real_lines = [
            f"일주 {day_pillar_kor}를 관계 쪽으로 읽으면 {day_pillar_line.replace(f'{day_pillar_kor} 일주는 ', '').rstrip('.')}",
            _pick(day_data["speech_style"], seed + 7),
            _pick(month_data["base_personality"], seed + 11),
            _pick(month_data["work_adaptation"], seed + 13),
        ]
        if time_data:
            context_real_lines.append(_pick(time_data["intimate_reaction"], seed + 17))

        context_action_lines = [
            f"세운 {year_fortune['ten_god']}와 대운 {year_fortune['daewoon_ten_god']}이 겹치는 해이므로, 감정보다 관계 속도를 먼저 조절하는 편이 좋습니다.",
            f"월지 {month_branch}의 리듬을 기준으로 보면 가까워지는 속도와 생활 호흡이 맞는지부터 확인하는 편이 좋습니다.",
        ]

        strengths.extend(
            _dedupe(
                [
                    _pick(month_data["base_personality"], seed + 19),
                    _pick(day_data["social_reaction"], seed + 23),
                ]
            )[:2]
        )
        if time_branch and time_branch in RELATIONSHIP_SPEED_WARNINGS:
            warnings.append(RELATIONSHIP_SPEED_WARNINGS[time_branch])

    if "겁재" in current_star_set or "상관" in current_star_set:
        warnings.append("관계에서는 말의 강약이 강해질 수 있어 서두른 확정은 피하는 편이 좋습니다.")
    if "정인" in current_star_set or "편인" in current_star_set:
        strengths.append("상대를 천천히 이해하려는 태도가 관계 안정에 도움이 됩니다.")
    day_pillar_kor = saju_result["saju"]["day"]["kor"] if saju_result else ""
    day_pillar_line = DAY_PILLAR_SENTENCES[day_pillar_kor]["relationship"] if saju_result else ""
    summary_prefix = f"{day_pillar_kor} 일주를 기준으로 보면 " if day_pillar_kor else ""
    summary = f"{summary_prefix}{RELATIONSHIP_PROFILE_SUMMARIES[relationship_profile]} {rule[intensity]}"
    explanation = f"{day_pillar_line} {_build_explanation(strength_profile, current_stars)} {RELATIONSHIP_PROFILE_SUMMARIES[relationship_profile]}".strip()
    advice = f"{_build_advice(strength_profile, current_star_set)} {RELATIONSHIP_PROFILE_ADVICE[relationship_profile]}"
    headline = _build_profile_headline(relationship_profile, strength_profile, intensity, day_pillar_kor or "이 원국")
    section = build_relationship_section(
        headline=headline,
        explanation=explanation,
        advice=advice,
        strengths=_dedupe(strengths)[:4],
        warnings=_dedupe(warnings)[:4],
        seed=len("".join(current_stars)) + len(strength_profile),
        context_easy_lines=context_easy_lines,
        context_real_lines=context_real_lines,
        context_action_lines=context_action_lines,
    )

    return {
        "headline": section["one_line"],
        "summary": summary,
        "explanation": " ".join(section["easy_explanation"]),
        "advice": " ".join(section["action_advice"]),
        "section": section,
        "trend": rule["trend"],
        "intensity": intensity,
        "intensity_kor": {"strong": "강", "medium": "보통", "light": "완만"}[intensity],
        "strengths": _dedupe(strengths)[:4],
        "warnings": _dedupe(warnings)[:4],
    }


def _resolve_intensity(stars: list[str], profile: str) -> str:
    if profile != "mixed" and stars[0] == stars[1]:
        return "strong"
    if any(star in {"겁재", "상관", "편재", "편관"} for star in stars):
        return "medium"
    return "light"


def _build_headline(profile: str, intensity: str) -> str:
    headline_map = {
        ("wealth", "strong"): "인연 유입은 강하지만 관계 속도 조절이 더 중요합니다.",
        ("wealth", "medium"): "새로운 만남 가능성은 있지만 서두르지 않는 편이 좋습니다.",
        ("wealth", "light"): "가벼운 접점을 넓히며 흐름을 지켜보기 좋은 시기입니다.",
        ("officer", "strong"): "관계 판단이 또렷해져 기준을 분명히 해야 하는 시기입니다.",
        ("officer", "medium"): "인연보다 관계의 안정성과 책임감을 먼저 볼 시기입니다.",
        ("officer", "light"): "천천히 관계 기준을 맞춰 가기 좋은 흐름입니다.",
        ("mixed", "strong"): "관계는 유지보다 재정비 흐름이 더 강하게 들어옵니다.",
        ("mixed", "medium"): "관계 속도보다 대화 방식 조정이 먼저입니다.",
        ("mixed", "light"): "감정의 결론을 서두르지 않으면 흐름이 부드럽습니다.",
    }
    return headline_map[(profile, intensity)]


def _build_profile_headline(relationship_profile: str, flow_profile: str, intensity: str, day_pillar_kor: str) -> str:
    flow_suffix = {
        ("wealth", "strong"): "지금은 만남이 들어와도 속도 조절이 더 중요합니다.",
        ("wealth", "medium"): "지금은 접점은 열리지만 서두르지 않는 편이 좋습니다.",
        ("wealth", "light"): "지금은 가벼운 접점을 넓히며 지켜보기 좋은 시기입니다.",
        ("officer", "strong"): "지금은 관계 기준을 분명히 해야 흐름이 살아납니다.",
        ("officer", "medium"): "지금은 안정성과 책임감을 먼저 보는 편이 맞습니다.",
        ("officer", "light"): "지금은 천천히 기준을 맞춰 가기 좋은 흐름입니다.",
        ("mixed", "strong"): "지금은 유지보다 재정비가 먼저인 시기입니다.",
        ("mixed", "medium"): "지금은 관계 속도보다 대화 방식 조정이 먼저입니다.",
        ("mixed", "light"): "지금은 결론을 서두르지 않으면 더 편안한 흐름입니다.",
    }[(flow_profile, intensity)]
    return f"{day_pillar_kor} 일주 기준으로는 {RELATIONSHIP_PROFILE_HEADLINES[relationship_profile].replace('관계는 ', '').rstrip('.')} {flow_suffix}"


def _build_explanation(profile: str, stars: list[str]) -> str:
    year_star, daewoon_star = stars
    profile_phrase = {
        "wealth": "사람과 감정 흐름이 바깥에서 들어오며 관계 속도가 빨라질 수 있습니다.",
        "officer": "관계의 기준과 책임감이 부각되어 감정보다 안정성이 먼저 보일 수 있습니다.",
        "mixed": "새 인연보다 현재 관계를 어떻게 조정할지가 더 중요하게 느껴질 수 있습니다.",
    }[profile]
    return (
        f"세운에서는 {year_star}, 대운에서는 {daewoon_star} 흐름이 겹칩니다. "
        f"{profile_phrase}"
    )


def _build_advice(profile: str, star_set: set[str]) -> str:
    if "겁재" in star_set or "상관" in star_set:
        return "호감이 생겨도 속도를 늦추고 말의 강약을 조절하는 편이 좋습니다."
    if profile == "wealth":
        return "인연이 보여도 감정만 보지 말고 생활 리듬과 현실 조건을 같이 보는 편이 좋습니다."
    if profile == "officer":
        return "상대 기준보다 내 기준을 먼저 분명히 해야 관계가 안정됩니다."
    return "관계를 바로 정의하기보다 대화 방식과 거리 조절부터 정리하는 편이 좋습니다."


def _pick(options: list[str], seed: int) -> str:
    return options[seed % len(options)]


def _resolve_relationship_profile(day_stem: str, month_branch: str, time_branch: str | None) -> str:
    if time_branch in {"축", "미", "술"} or month_branch in {"축", "미"}:
        return "slow_trust"
    if time_branch in {"사", "오"} or day_stem in {"병", "정"}:
        return "expressive"
    if time_branch in {"신", "유"} or day_stem in {"경", "신"}:
        return "boundary_first"
    if time_branch in {"자", "해"} or day_stem in {"임", "계"}:
        return "observer"
    if month_branch in {"묘", "진"} or day_stem in {"을", "기"}:
        return "balanced_connector"
    return "pace_adjuster"


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
