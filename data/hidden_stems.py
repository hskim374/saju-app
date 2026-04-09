"""Hidden stem tables for each earthly branch."""

from __future__ import annotations

BRANCH_HIDDEN_STEMS = {
    "자": [{"stem": "계", "weight": 1.0}],
    "축": [
        {"stem": "기", "weight": 0.6},
        {"stem": "계", "weight": 0.25},
        {"stem": "신", "weight": 0.15},
    ],
    "인": [
        {"stem": "갑", "weight": 0.6},
        {"stem": "병", "weight": 0.25},
        {"stem": "무", "weight": 0.15},
    ],
    "묘": [{"stem": "을", "weight": 1.0}],
    "진": [
        {"stem": "무", "weight": 0.6},
        {"stem": "을", "weight": 0.25},
        {"stem": "계", "weight": 0.15},
    ],
    "사": [
        {"stem": "병", "weight": 0.6},
        {"stem": "경", "weight": 0.25},
        {"stem": "무", "weight": 0.15},
    ],
    "오": [
        {"stem": "정", "weight": 0.7},
        {"stem": "기", "weight": 0.3},
    ],
    "미": [
        {"stem": "기", "weight": 0.6},
        {"stem": "정", "weight": 0.25},
        {"stem": "을", "weight": 0.15},
    ],
    "신": [
        {"stem": "경", "weight": 0.6},
        {"stem": "임", "weight": 0.25},
        {"stem": "무", "weight": 0.15},
    ],
    "유": [{"stem": "신", "weight": 1.0}],
    "술": [
        {"stem": "무", "weight": 0.6},
        {"stem": "신", "weight": 0.25},
        {"stem": "정", "weight": 0.15},
    ],
    "해": [
        {"stem": "임", "weight": 0.7},
        {"stem": "갑", "weight": 0.3},
    ],
}


def get_hidden_stems(branch: str) -> list[dict[str, float | str]]:
    """Return the hidden stems configured for a branch."""
    return BRANCH_HIDDEN_STEMS.get(branch, [])
