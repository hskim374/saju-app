"""Detailed pillar helpers: 12-stage, hidden stems, and hap/chung summaries."""

from __future__ import annotations

from data.branches import BRANCHES_BY_HANJA, BRANCHES_BY_KOR
from data.hidden_stems import get_hidden_stems
from data.stems import STEMS_BY_HANJA, STEMS_BY_KOR

PILLAR_ORDER = ("year", "month", "day", "time")

TWELVE_STATES_BY_DAY_STEM = {
    "갑": {
        "자": "목욕",
        "축": "관대",
        "인": "건록",
        "묘": "제왕",
        "진": "쇠",
        "사": "병",
        "오": "사",
        "미": "묘",
        "신": "절",
        "유": "태",
        "술": "양",
        "해": "장생",
    },
    "을": {
        "자": "병",
        "축": "쇠",
        "인": "제왕",
        "묘": "건록",
        "진": "관대",
        "사": "목욕",
        "오": "장생",
        "미": "양",
        "신": "태",
        "유": "절",
        "술": "묘",
        "해": "사",
    },
    "병": {
        "자": "태",
        "축": "양",
        "인": "장생",
        "묘": "목욕",
        "진": "관대",
        "사": "건록",
        "오": "제왕",
        "미": "쇠",
        "신": "병",
        "유": "사",
        "술": "묘",
        "해": "절",
    },
    "정": {
        "자": "절",
        "축": "묘",
        "인": "사",
        "묘": "병",
        "진": "쇠",
        "사": "제왕",
        "오": "건록",
        "미": "관대",
        "신": "목욕",
        "유": "장생",
        "술": "양",
        "해": "태",
    },
    "무": {
        "자": "태",
        "축": "양",
        "인": "장생",
        "묘": "목욕",
        "진": "관대",
        "사": "건록",
        "오": "제왕",
        "미": "쇠",
        "신": "병",
        "유": "사",
        "술": "묘",
        "해": "절",
    },
    "기": {
        "자": "절",
        "축": "묘",
        "인": "사",
        "묘": "병",
        "진": "쇠",
        "사": "제왕",
        "오": "건록",
        "미": "관대",
        "신": "목욕",
        "유": "장생",
        "술": "양",
        "해": "태",
    },
    "경": {
        "자": "사",
        "축": "묘",
        "인": "절",
        "묘": "태",
        "진": "양",
        "사": "장생",
        "오": "목욕",
        "미": "관대",
        "신": "건록",
        "유": "제왕",
        "술": "쇠",
        "해": "병",
    },
    "신": {
        "자": "장생",
        "축": "양",
        "인": "태",
        "묘": "절",
        "진": "묘",
        "사": "사",
        "오": "병",
        "미": "쇠",
        "신": "제왕",
        "유": "건록",
        "술": "관대",
        "해": "목욕",
    },
    "임": {
        "자": "제왕",
        "축": "쇠",
        "인": "병",
        "묘": "사",
        "진": "묘",
        "사": "절",
        "오": "태",
        "미": "양",
        "신": "장생",
        "유": "목욕",
        "술": "관대",
        "해": "건록",
    },
    "계": {
        "자": "건록",
        "축": "관대",
        "인": "목욕",
        "묘": "장생",
        "진": "양",
        "사": "태",
        "오": "절",
        "미": "묘",
        "신": "사",
        "유": "병",
        "술": "쇠",
        "해": "제왕",
    },
}

INTERACTION_ORDER = ("합", "충", "형", "파", "해", "원진")


def build_pillar_details(*, saju: dict, interactions: dict | None = None) -> dict:
    """Build all pillar detail payloads in one pass."""
    hidden_stems = extract_hidden_stems_by_pillar(saju)
    return {
        "twelve_states": calculate_twelve_states(saju),
        "hidden_stems": hidden_stems["by_pillar"],
        "hidden_stems_text": hidden_stems["text_by_pillar"],
        "hapchung": summarize_hapchung(interactions or {}),
    }


def calculate_twelve_states(saju: dict) -> dict[str, str | None]:
    """Calculate 12-stage labels by pillar based on day stem and branch."""
    day_stem = _to_kor_stem(saju["day"]["stem"])
    if day_stem is None or day_stem not in TWELVE_STATES_BY_DAY_STEM:
        return {role: None for role in PILLAR_ORDER}

    stage_map = TWELVE_STATES_BY_DAY_STEM[day_stem]
    result: dict[str, str | None] = {}
    for role in PILLAR_ORDER:
        pillar = saju.get(role)
        if pillar is None:
            result[role] = None
            continue
        branch = _to_kor_branch(pillar.get("branch"))
        result[role] = None if branch is None else stage_map.get(branch)
    return result


def extract_hidden_stems_by_pillar(saju: dict) -> dict[str, dict]:
    """Extract hidden stems (지장간) for each pillar branch."""
    by_pillar: dict[str, list[dict]] = {}
    text_by_pillar: dict[str, str] = {}

    for role in PILLAR_ORDER:
        pillar = saju.get(role)
        if pillar is None:
            by_pillar[role] = []
            text_by_pillar[role] = "미산출"
            continue

        branch = _to_kor_branch(pillar.get("branch"))
        if branch is None:
            by_pillar[role] = []
            text_by_pillar[role] = "-"
            continue

        rows: list[dict] = []
        for hidden in get_hidden_stems(branch):
            stem = str(hidden.get("stem", "")).strip()
            if stem not in STEMS_BY_KOR:
                continue
            stem_meta = STEMS_BY_KOR[stem]
            rows.append(
                {
                    "stem": stem,
                    "hanja": stem_meta["hanja"],
                    "display": f"{stem}({stem_meta['hanja']})",
                    "weight": float(hidden.get("weight", 0.0)),
                }
            )

        by_pillar[role] = rows
        text_by_pillar[role] = " · ".join(item["display"] for item in rows) if rows else "-"

    return {
        "by_pillar": by_pillar,
        "text_by_pillar": text_by_pillar,
    }


def summarize_hapchung(interactions: dict) -> dict:
    """Summarize natal interactions with a dedicated 합/충 focus."""
    by_type = {key: [] for key in INTERACTION_ORDER}
    for item in interactions.get("natal", []):
        interaction_type = str(item.get("type", "")).strip()
        target = str(item.get("target", "")).strip()
        if interaction_type not in by_type or not target:
            continue
        if target not in by_type[interaction_type]:
            by_type[interaction_type].append(target)

    counts = {key: len(value) for key, value in by_type.items()}
    summary = _build_hapchung_summary_line(counts)
    return {
        "natal": by_type,
        "counts": counts,
        "has_hap": counts["합"] > 0,
        "has_chung": counts["충"] > 0,
        "summary": summary,
    }


def _build_hapchung_summary_line(counts: dict[str, int]) -> str:
    if counts["합"] and counts["충"]:
        return "원국에 합과 충이 함께 있어 연결과 충돌이 동시에 작동하는 구조입니다."
    if counts["충"]:
        return "원국에 충 신호가 있어 일정·관계·선택의 마찰 관리가 중요합니다."
    if counts["합"]:
        return "원국에 합 신호가 있어 조건을 맞추면 흐름을 부드럽게 이어가기 쉬운 편입니다."
    return "원국 기준으로 강한 합충 신호는 두드러지지 않아 기본 리듬 유지가 유리합니다."


def _to_kor_stem(value: str | None) -> str | None:
    if value is None:
        return None
    if value in STEMS_BY_KOR:
        return value
    if value in STEMS_BY_HANJA:
        return STEMS_BY_HANJA[value]["kor"]
    return None


def _to_kor_branch(value: str | None) -> str | None:
    if value is None:
        return None
    if value in BRANCHES_BY_KOR:
        return value
    if value in BRANCHES_BY_HANJA:
        return BRANCHES_BY_HANJA[value]["kor"]
    return None

