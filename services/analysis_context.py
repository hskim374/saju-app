"""Build the richer intermediate analysis context used by the interpretation layer."""

from __future__ import annotations

from services.evidence_trace import build_evidence_trace
from services.interactions import calculate_luck_interactions, calculate_natal_interactions
from services.interpretation_rules import build_analysis_flags
from services.strength_model import calculate_strength_analysis
from services.yongshin import calculate_yongshin_candidates


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
    flags = build_analysis_flags(
        saju=saju,
        element_analysis=element_analysis,
        strength_analysis=strength,
        yongshin_analysis=yongshin,
        interaction_analysis=interactions,
        ten_god_analysis=ten_gods,
    )
    uncertainty_notes = _build_uncertainty_notes(saju, yongshin)
    evidence = {
        "overall": build_evidence_trace(
            section="overall",
            conclusions=[strength["display_label"], yongshin["display"]["primary"]],
            facts=[
                f"dominant={','.join(element_analysis['dominant'])}",
                f"weak={','.join(element_analysis['weak'])}",
                f"strength={strength['label']}",
            ],
            rules=["weighted_elements", "strength_model", "yongshin_candidates"],
            confidence=yongshin["confidence"],
            uncertainty_notes=uncertainty_notes,
        )
    }

    return {
        "pillars": saju,
        "elements": element_analysis,
        "strength": strength,
        "yongshin": yongshin,
        "interactions": interactions,
        "ten_gods": ten_gods,
        "flags": flags,
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
