"""Interaction detection for natal and luck pillars."""

from __future__ import annotations

from itertools import combinations

from services.report_display import format_branch_label, format_stem_label

STEM_COMBINATIONS = {
    frozenset(("갑", "기")): "현실과 방향을 묶어 주는 합으로 읽힐 수 있습니다.",
    frozenset(("을", "경")): "관계 조율과 결단이 함께 들어오는 합으로 볼 수 있습니다.",
    frozenset(("병", "신")): "표현과 판단이 맞물리는 합으로 읽힐 수 있습니다.",
    frozenset(("정", "임")): "감정선과 흐름 감각이 서로 얽히는 합으로 볼 수 있습니다.",
    frozenset(("무", "계")): "운영과 조절이 만나는 합으로 해석할 수 있습니다.",
}

BRANCH_COMBINATIONS = {
    "합": {
        frozenset(("자", "축")): "생활 기반을 단단히 묶는 합으로 보기 쉽습니다.",
        frozenset(("인", "해")): "확장성과 준비 흐름이 만나 방향을 넓히는 합으로 읽힙니다.",
        frozenset(("묘", "술")): "관계와 책임이 서로 보완되는 합으로 읽힙니다.",
        frozenset(("진", "유")): "정리와 운영 감각이 이어지는 합으로 볼 수 있습니다.",
        frozenset(("사", "신")): "움직임과 결과 정리가 서로 엮이는 합으로 해석할 수 있습니다.",
        frozenset(("오", "미")): "표현과 안정이 맞물리는 합으로 보기 쉽습니다.",
    },
    "충": {
        frozenset(("자", "오")): "속도와 감정 반응이 충돌해 리듬 차이가 크게 날 수 있습니다.",
        frozenset(("축", "미")): "생활 기준과 현실 운영 방식이 부딪힐 수 있습니다.",
        frozenset(("인", "신")): "확장과 결론 방식이 부딪혀 방향 전환 압력이 커질 수 있습니다.",
        frozenset(("묘", "유")): "관계 감각과 기준 정리가 정면으로 부딪히기 쉬운 충입니다.",
        frozenset(("진", "술")): "버티는 방식과 책임 기준이 충돌할 수 있습니다.",
        frozenset(("사", "해")): "반응 속도와 여유를 보는 시각이 크게 어긋날 수 있습니다.",
    },
    "형": {
        frozenset(("인", "사")): "판단 속도와 욕구가 엇갈려 긴장이 커질 수 있습니다.",
        frozenset(("사", "신")): "속도와 결과 압박이 겹쳐 예민함이 올라갈 수 있습니다.",
        frozenset(("인", "신")): "확장과 통제 기준이 동시에 밀려와 피로가 커질 수 있습니다.",
        frozenset(("축", "술")): "책임과 기준이 딱딱하게 굳어 융통성이 줄 수 있습니다.",
        frozenset(("술", "미")): "버티는 힘이 과해져 변화 전환이 늦어질 수 있습니다.",
        frozenset(("축", "미")): "생활 운영 방식이 얽혀 답답함이 커질 수 있습니다.",
        frozenset(("자", "묘")): "감정 반응과 관계 감각이 어긋나 예민함이 올라갈 수 있습니다.",
    },
    "파": {
        frozenset(("자", "유")): "작은 기준 차이가 관계나 결과에 금을 낼 수 있습니다.",
        frozenset(("축", "진")): "운영 질서와 정리 방식에 잔갈등이 남을 수 있습니다.",
        frozenset(("인", "해")): "확장과 여유의 간격 조절이 흐트러질 수 있습니다.",
        frozenset(("묘", "오")): "감정 속도 차이로 일정과 관계가 흔들릴 수 있습니다.",
        frozenset(("신", "사")): "성과 압박이 커져 과열이 남기 쉬운 파입니다.",
        frozenset(("미", "술")): "버티는 기준이 서로 엇갈려 마찰이 쌓일 수 있습니다.",
    },
    "해": {
        frozenset(("자", "미")): "생활 감각이 어긋나 피로가 누적될 수 있습니다.",
        frozenset(("축", "오")): "현실 기준과 반응 속도가 어긋나 마음고생이 생길 수 있습니다.",
        frozenset(("인", "사")): "앞으로 나가려는 힘과 속도 조절이 어긋날 수 있습니다.",
        frozenset(("묘", "진")): "관계 감각과 현실 판단이 서로 걸릴 수 있습니다.",
        frozenset(("신", "해")): "정리와 여유를 보는 방식이 달라 판단 피로가 생길 수 있습니다.",
        frozenset(("유", "술")): "기준과 책임이 겹쳐 관계 온도가 낮아질 수 있습니다.",
    },
}


def calculate_natal_interactions(saju: dict) -> dict:
    """Detect interactions inside the natal chart."""
    pillars = [(role, pillar) for role, pillar in saju.items() if pillar is not None]
    entries: list[dict] = []

    for (left_role, left), (right_role, right) in combinations(pillars, 2):
        entries.extend(_resolve_pair(left_role, left, right_role, right))

    return {
        "natal": entries,
        "with_daewoon": [],
        "with_yearly": [],
        "with_daily": [],
    }


def calculate_luck_interactions(
    saju: dict,
    *,
    daewoon: dict | None = None,
    yearly: dict | None = None,
    daily: dict | None = None,
) -> dict:
    """Detect interactions between natal pillars and incoming luck pillars."""
    return {
        "natal": [],
        "with_daewoon": _resolve_external_interactions(saju, daewoon, "대운"),
        "with_yearly": _resolve_external_interactions(saju, yearly, "세운"),
        "with_daily": _resolve_external_interactions(saju, daily, "일운"),
    }


def _resolve_external_interactions(saju: dict, external: dict | None, label: str) -> list[dict]:
    if not external:
        return []

    pillar = {
        "stem": external.get("stem"),
        "branch": external.get("branch"),
        "kor": external.get("pillar"),
    }
    if not pillar["stem"] or not pillar["branch"]:
        return []

    entries: list[dict] = []
    for role, natal_pillar in saju.items():
        if natal_pillar is None:
            continue
        entries.extend(_resolve_pair(role, natal_pillar, label, pillar))
    return entries


def _resolve_pair(left_role: str, left: dict, right_role: str, right: dict) -> list[dict]:
    entries: list[dict] = []
    stem_key = frozenset((left["stem"], right["stem"]))
    if stem_key in STEM_COMBINATIONS:
        entries.append(
            _entry(
                interaction_type="합",
                source=f"{left_role}-{right_role}",
                target=f"{format_stem_label(left['stem'])}-{format_stem_label(right['stem'])}",
                strength="medium",
                meaning=STEM_COMBINATIONS[stem_key],
            )
        )

    branch_key = frozenset((left["branch"], right["branch"]))
    for interaction_type, mapping in BRANCH_COMBINATIONS.items():
        if branch_key not in mapping:
            continue
        entries.append(
            _entry(
                interaction_type=interaction_type,
                source=f"{left_role}-{right_role}",
                target=f"{format_branch_label(left['branch'])}-{format_branch_label(right['branch'])}",
                strength="high" if interaction_type in {"충", "형"} else "medium",
                meaning=mapping[branch_key],
            )
        )
    return entries


def _entry(*, interaction_type: str, source: str, target: str, strength: str, meaning: str) -> dict:
    return {
        "type": interaction_type,
        "source": source,
        "target": target,
        "strength": strength,
        "meaning": meaning,
    }
