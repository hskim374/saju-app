"""Category/question catalog for extra saju reading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CATALOG_PATH = Path("data/extra_reading_categories.json")


def _load_catalog() -> list[dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return []
    try:
        raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    categories = raw.get("categories") if isinstance(raw, dict) else None
    if not isinstance(categories, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in categories:
        if not isinstance(item, dict):
            continue
        category_id = str(item.get("id") or "").strip()
        label = str(item.get("label") or "").strip()
        questions = item.get("questions")
        if not category_id or not label or not isinstance(questions, list):
            continue
        question_list = [str(q).strip() for q in questions if str(q).strip()]
        if not question_list:
            continue
        normalized.append(
            {
                "id": category_id,
                "label": label,
                "questions": question_list,
            }
        )
    return normalized


def get_categories() -> list[dict[str, Any]]:
    """Return category list for UI."""
    return [
        {
            "id": item["id"],
            "label": item["label"],
            "question_count": len(item["questions"]),
        }
        for item in _load_catalog()
    ]


def get_questions(category_id: str) -> list[str]:
    category_id = str(category_id or "").strip()
    if not category_id:
        return []
    for item in _load_catalog():
        if item["id"] == category_id:
            return item["questions"][:]
    return []


def get_category_label(category_id: str) -> str:
    category_id = str(category_id or "").strip()
    if not category_id:
        return ""
    for item in _load_catalog():
        if item["id"] == category_id:
            return item["label"]
    return ""


def is_valid_category_question(category_id: str, question: str) -> bool:
    question = str(question or "").strip()
    if not question:
        return False
    return question in get_questions(category_id)

