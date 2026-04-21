"""Build the richer intermediate analysis context used by the interpretation layer."""

from __future__ import annotations

from data.branches import BRANCHES
from data.stems import STEMS
from services.evidence_trace import build_evidence_trace
from services.interactions import calculate_luck_interactions, calculate_natal_interactions
from services.interpretation_rules import build_analysis_flags
from services.pillar_details import build_pillar_details
from services.special_stars import calculate_special_stars
from services.structure_analyzer import analyze_structure
from services.strength_model import calculate_strength_analysis
from services.yongshin import calculate_yongshin_candidates

STEM_KOR_SET = {item["kor"] for item in STEMS}
STEM_HANJA_SET = {item["hanja"] for item in STEMS}
BRANCH_KOR_SET = {item["kor"] for item in BRANCHES}
BRANCH_HANJA_SET = {item["hanja"] for item in BRANCHES}

PILLAR_ROLES = {
    "year": "외부 환경",
    "month": "사회/직업 환경",
    "day": "본체/배우자",
    "hour": "결과/후반 인생",
}


def build_analysis_context(
    *,
    saju_result: dict,
    element_analysis: dict,
    ten_gods: dict,
    daewoon: dict | None = None,
    year_fortune: dict | None = None,
    daily_fortune: dict | None = None,
) -> dict:
    """Assemble the intermediate domain-analysis layer."""
    saju = saju_result["saju"]
    strength = calculate_strength_analysis(saju, element_analysis)
    yongshin = calculate_yongshin_candidates(saju, element_analysis, strength)
    natal_interactions = calculate_natal_interactions(saju)
    luck_interactions = calculate_luck_interactions(
        saju,
        daewoon=daewoon["active_cycle_summary"] if daewoon else None,
        yearly=year_fortune,
        daily=daily_fortune,
    )
    interactions = {
        "natal": natal_interactions["natal"],
        "with_daewoon": luck_interactions["with_daewoon"],
        "with_yearly": luck_interactions["with_yearly"],
        "with_daily": luck_interactions["with_daily"],
    }
    pillar_details = build_pillar_details(
        saju=saju,
        interactions=interactions,
    )
    special_stars = calculate_special_stars(saju)
    structure = analyze_structure(
        saju=saju,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        strength_analysis=strength,
        yongshin_analysis=yongshin,
        interactions=interactions,
    )
    flags = build_analysis_flags(
        saju=saju,
        element_analysis=element_analysis,
        strength_analysis=strength,
        yongshin_analysis=yongshin,
        interaction_analysis=interactions,
        ten_god_analysis=ten_gods,
    )
    uncertainty_notes = _build_uncertainty_notes(saju, yongshin)
    relation_matrix = _build_relation_matrix(interactions["natal"])
    analysis_payload = _build_analysis_payload(
        saju=saju,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        strength=strength,
        structure=structure,
        yongshin=yongshin,
        relation_matrix=relation_matrix,
    )
    evidence = {
        "overall": build_evidence_trace(
            section="overall",
            conclusions=[strength["display_label"], yongshin["display"]["primary"]],
            facts=[
                f"dominant={','.join(element_analysis['dominant'])}",
                f"weak={','.join(element_analysis['weak'])}",
                f"strength={strength['label']}",
                f"pattern={structure['primary_pattern']}",
                f"special_stars={','.join(special_stars['tags']) or 'none'}",
            ],
            rules=["weighted_elements", "strength_model", "yongshin_candidates", "structure_analyzer", "special_stars_basic"],
            confidence=yongshin["confidence"],
            uncertainty_notes=uncertainty_notes,
        )
    }

    return {
        "saju_id": saju_result.get("saju_id"),
        "pillars": saju,
        "elements": element_analysis,
        "strength": strength,
        "yongshin": yongshin,
        "interactions": interactions,
        "relations": relation_matrix,
        "pillar_roles": PILLAR_ROLES,
        "twelve_states": pillar_details["twelve_states"],
        "hidden_stems": pillar_details["hidden_stems"],
        "hidden_stems_text": pillar_details["hidden_stems_text"],
        "hapchung": pillar_details["hapchung"],
        "special_stars": special_stars,
        "structure": structure,
        "ten_gods": ten_gods,
        "flags": flags,
        "analysis": analysis_payload,
        "evidence": evidence,
        "uncertainty_notes": uncertainty_notes,
    }


def _build_uncertainty_notes(saju: dict, yongshin: dict) -> list[str]:
    notes: list[str] = []
    if saju.get("time") is None:
        notes.append("출생시간이 없어 시주와 일부 세부 해석은 보수적으로 읽었습니다.")
    if yongshin["confidence"] != "high":
        notes.append(
            f"용신 후보는 {yongshin['confidence_display']} 확신도로 읽혀 보조 후보를 함께 보는 편이 안전합니다."
        )
    if not notes:
        notes.append("현재 계산 기준에서는 원국 구조가 비교적 안정적으로 읽히는 편입니다.")
    return notes


def _build_relation_matrix(natal_interactions: list[dict]) -> dict:
    relations = {
        "stem_combinations": [],
        "stem_clashes": [],
        "branch_combinations": [],
        "branch_clashes": [],
        "harms": [],
        "punishments": [],
        "breaks": [],
        "wonjin": [],
    }

    for item in natal_interactions:
        kind = _target_kind(item.get("target", ""))
        interaction_type = item.get("type")
        if interaction_type == "합":
            key = "stem_combinations" if kind == "stem" else "branch_combinations"
            relations[key].append(item)
        elif interaction_type == "충":
            key = "stem_clashes" if kind == "stem" else "branch_clashes"
            relations[key].append(item)
        elif interaction_type == "해":
            relations["harms"].append(item)
        elif interaction_type == "형":
            relations["punishments"].append(item)
        elif interaction_type == "파":
            relations["breaks"].append(item)
        elif interaction_type == "원진":
            relations["wonjin"].append(item)
    return relations


def _target_kind(target: str) -> str:
    left = target.split("-")[0][:1] if target else ""
    if left in STEM_KOR_SET or left in STEM_HANJA_SET:
        return "stem"
    if left in BRANCH_KOR_SET or left in BRANCH_HANJA_SET:
        return "branch"
    return "branch"


def _build_analysis_payload(
    *,
    saju: dict,
    element_analysis: dict,
    ten_gods: dict,
    strength: dict,
    structure: dict,
    yongshin: dict,
    relation_matrix: dict,
) -> dict:
    visible_ten_gods = [value for value in ten_gods["visible"].values() if value]
    hidden_ten_gods = [
        value
        for values in ten_gods["hidden"].values()
        for value in values
        if value
    ]

    return {
        "day_master": saju["day"]["stem"],
        "season": structure["season"],
        "month_branch": saju["month"]["branch"],
        "strength": {
            "score": strength["score"],
            "label": strength["label"],
        },
        "five_elements": element_analysis["weighted_scores"],
        "dominant_elements": element_analysis["dominant"],
        "lacking_elements": element_analysis["weak"],
        "ten_gods": {
            "visible": visible_ten_gods,
            "hidden": hidden_ten_gods,
        },
        "structure": {
            "primary_pattern": structure["primary_pattern"],
            "sub_pattern": structure["sub_pattern"],
        },
        "useful_gods": {
            "yongshin": yongshin["primary_candidate"],
            "heeshin": yongshin.get("heeshin", []),
            "kishin": yongshin.get("kishin", []),
        },
        "relations": relation_matrix,
        "pillar_roles": PILLAR_ROLES,
    }
