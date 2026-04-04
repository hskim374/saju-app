"""Load structured interpretation sentence pools from JSON."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "analysis_sentences.json"


@lru_cache(maxsize=1)
def load_analysis_sentences() -> dict:
    """Return cached sentence pools for high-density interpretation branching."""
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))
