"""Compatibility wrapper for the new narrative interpretation engine."""

from __future__ import annotations

from services.interpretation_engine import build_interpretation_payload


def build_interpretation(
    element_analysis: dict,
    ten_gods: dict | None = None,
    daewoon: dict | None = None,
    year_fortune: dict | None = None,
    saju_result: dict | None = None,
    analysis_context: dict | None = None,
) -> dict:
    """Build interpretation payload while preserving legacy keys."""
    return build_interpretation_payload(
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        saju_result=saju_result,
        analysis_context=analysis_context,
    )
