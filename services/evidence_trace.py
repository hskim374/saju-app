"""Helpers for explicit conclusion-to-evidence traces."""

from __future__ import annotations


def build_evidence_trace(
    *,
    section: str,
    conclusions: list[str],
    facts: list[str],
    rules: list[str],
    confidence: str,
    uncertainty_notes: list[str] | None = None,
) -> list[dict]:
    """Package simple evidence records for explainability output."""
    return [
        {
            "section": section,
            "conclusion": conclusion,
            "facts": facts,
            "rules": rules,
            "confidence": confidence,
            "uncertainty_notes": uncertainty_notes or [],
        }
        for conclusion in conclusions
    ]
