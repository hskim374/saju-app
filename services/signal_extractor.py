"""Extract interpretation signals from structure-rich analysis context."""

from __future__ import annotations


def extract_interpretation_signals(analysis_context: dict) -> dict:
    """Return layered signals used by condition-based sentence matching."""
    structure = analysis_context["structure"]
    strength = analysis_context["strength"]
    flags = analysis_context["flags"]
    yongshin = analysis_context["yongshin"]["display"]
    ten_gods = analysis_context["ten_gods"]["ten_gods"]

    signals = {
        "core": [
            f"{structure['season_label']} 출생",
            f"{strength['display_label']} 경향",
            f"{structure['primary_pattern']} 구조",
        ],
        "personality": [],
        "career": [],
        "money": [],
        "relationship": [],
        "health": [],
        "risk": [],
        "luck": [],
    }

    if flags["is_day_master_weak"]:
        signals["core"].append("환경 민감형")
        signals["risk"].append("과부하 취약")
        signals["health"].append("회복 우선형")
    if flags["is_day_master_strong"]:
        signals["core"].append("추진 과열 주의형")
        signals["risk"].append("과속 리스크")

    month_ten_god = ten_gods.get("month")
    if month_ten_god in {"식신", "상관"}:
        signals["career"].extend(["생산형", "표현형"])
    if month_ten_god in {"편재", "정재"}:
        signals["money"].extend(["재성 운영형", "실무 수익형"])
    if month_ten_god in {"편관", "정관"}:
        signals["career"].append("책임형")
        signals["relationship"].append("기준 중시형")

    if flags["wealth_flow_open"]:
        signals["money"].append("흐름 개방형")
    if flags["has_natal_conflict"]:
        signals["relationship"].append("관계 조율 필요")
        signals["risk"].append("충돌 관리 필요")
    if flags["has_natal_harmony"]:
        signals["relationship"].append("연결 회복 가능")

    signals["luck"].append(f"용신 중심: {yongshin['primary']}")
    signals["luck"].append(f"보조 축: {yongshin['secondary']}")

    return signals

