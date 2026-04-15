"""Stable chart identification helpers for the three-layer pipeline."""

from __future__ import annotations

from hashlib import md5

PILLAR_ORDER = ("year", "month", "day", "hour")


def build_saju_id(saju: dict) -> str:
    """Return a deterministic, human-readable chart id."""
    segments: list[str] = []
    for role in PILLAR_ORDER:
        pillar = _pillar_for_role(saju, role)
        if not pillar:
            segments.append(f"{role}-unknown")
            continue
        segments.append(f"{role}-{pillar['stem']}{pillar['branch']}")
    return "|".join(segments)


def build_saju_hash(saju_id: str) -> str:
    """Return a short hash for cache/index keys."""
    return md5(saju_id.encode("utf-8")).hexdigest()


def build_saju_identity(saju: dict) -> dict:
    """Return full identity payload for storage and caching hooks."""
    saju_id = build_saju_id(saju)
    return {
        "saju_id": saju_id,
        "saju_hash": build_saju_hash(saju_id),
    }


def _pillar_for_role(saju: dict, role: str) -> dict | None:
    if role == "hour":
        return saju.get("time")
    return saju.get(role)
