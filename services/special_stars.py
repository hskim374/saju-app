"""Basic special-star (신살) detection layer for interpretation context."""

from __future__ import annotations

from collections import defaultdict

STAR_GROUP_RULES = {
    "도화": {
        "targets": {
            "申子辰": "유",
            "寅午戌": "묘",
            "亥卯未": "자",
            "巳酉丑": "오",
        },
        "meaning": "관계/표현/주목도 흐름이 강해지는 경향",
        "tone": "relationship",
    },
    "역마": {
        "targets": {
            "申子辰": "인",
            "寅午戌": "신",
            "亥卯未": "사",
            "巳酉丑": "해",
        },
        "meaning": "이동/변화/환경 전환이 잦아질 수 있는 흐름",
        "tone": "movement",
    },
    "화개": {
        "targets": {
            "申子辰": "진",
            "寅午戌": "술",
            "亥卯未": "미",
            "巳酉丑": "축",
        },
        "meaning": "정리/집중/내면 몰입이 커질 수 있는 흐름",
        "tone": "focus",
    },
}

GROUP_BY_BRANCH = {
    "신": "申子辰",
    "자": "申子辰",
    "진": "申子辰",
    "인": "寅午戌",
    "오": "寅午戌",
    "술": "寅午戌",
    "해": "亥卯未",
    "묘": "亥卯未",
    "미": "亥卯未",
    "사": "巳酉丑",
    "유": "巳酉丑",
    "축": "巳酉丑",
}


def calculate_special_stars(saju: dict) -> dict:
    """Detect a small, stable set of stars from day/year branch groups."""
    branch_by_pillar = {
        "year": saju["year"]["branch"],
        "month": saju["month"]["branch"],
        "day": saju["day"]["branch"],
    }
    if saju.get("time"):
        branch_by_pillar["time"] = saju["time"]["branch"]

    active_entries: list[dict] = []
    for source in ("day", "year"):
        source_branch = branch_by_pillar[source]
        group = GROUP_BY_BRANCH[source_branch]
        for star_name, star_rule in STAR_GROUP_RULES.items():
            target_branch = star_rule["targets"][group]
            matched_pillars = [pillar for pillar, branch in branch_by_pillar.items() if branch == target_branch]
            if not matched_pillars:
                continue
            active_entries.append(
                {
                    "name": star_name,
                    "source": source,
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "matched_pillars": matched_pillars,
                    "meaning": star_rule["meaning"],
                    "tone": star_rule["tone"],
                }
            )

    deduped = _dedupe_entries(active_entries)
    summary = _build_summary(deduped)
    return {
        "active": deduped,
        "summary": summary,
        "tags": [item["name"] for item in deduped],
        "has_relationship_star": any(item["tone"] == "relationship" for item in deduped),
        "has_movement_star": any(item["tone"] == "movement" for item in deduped),
        "has_focus_star": any(item["tone"] == "focus" for item in deduped),
    }


def _dedupe_entries(entries: list[dict]) -> list[dict]:
    bucket: dict[tuple[str, str], dict] = {}
    for entry in entries:
        key = (entry["name"], entry["target_branch"])
        if key not in bucket:
            bucket[key] = {
                **entry,
                "source": [entry["source"]],
                "matched_pillars": set(entry["matched_pillars"]),
            }
            continue
        bucket[key]["source"].append(entry["source"])
        bucket[key]["matched_pillars"].update(entry["matched_pillars"])

    deduped: list[dict] = []
    for item in bucket.values():
        normalized = {
            **item,
            "source": sorted(set(item["source"])),
            "matched_pillars": sorted(item["matched_pillars"]),
        }
        deduped.append(normalized)

    deduped.sort(key=lambda value: (value["name"], value["target_branch"]))
    return deduped


def _build_summary(active: list[dict]) -> list[str]:
    if not active:
        return ["기본 신살 흐름은 비교적 단순해 과도한 이벤트성 변동은 낮은 편입니다."]

    tone_map = defaultdict(list)
    for item in active:
        tone_map[item["tone"]].append(item["name"])

    summary: list[str] = []
    if tone_map["relationship"]:
        summary.append("관계/표현 흐름이 강해져 대인 반응과 주목도가 동시에 올라오기 쉬운 편입니다.")
    if tone_map["movement"]:
        summary.append("이동/전환 신호가 있어 환경 변화나 역할 변경에 대한 대응이 중요해집니다.")
    if tone_map["focus"]:
        summary.append("집중/정리 흐름이 들어와 혼자 정리하거나 마무리 완성도를 높이는 힘이 살아납니다.")
    if not summary:
        summary.append("신살 흐름은 있으나 강한 충돌보다 생활 리듬 조정 쪽에서 먼저 체감되는 편입니다.")
    return summary

