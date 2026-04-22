"""Daily free-usage limiter and event logger for extra reading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import Request

USAGE_STORE_PATH = Path(os.getenv("EXTRA_READING_USAGE_STORE_PATH", "logs/extra_reading_usage.json"))
EVENT_LOG_PATH = Path(os.getenv("EXTRA_READING_EVENT_LOG_PATH", "logs/extra_reading_events.jsonl"))
FREE_DAILY_LIMIT = 2
COOKIE_KEY = "saju_uid"
KST = timezone(timedelta(hours=9), name="KST")

_LOCK = Lock()


@dataclass(frozen=True)
class UsageStatus:
    limit: int
    used: int
    remaining: int
    date: str
    blocked: bool


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_store() -> dict[str, dict[str, int]]:
    if not USAGE_STORE_PATH.exists():
        return {}
    try:
        raw = json.loads(USAGE_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, int]] = {}
    for date_key, rows in raw.items():
        if not isinstance(rows, dict):
            continue
        normalized_rows: dict[str, int] = {}
        for user_key, count in rows.items():
            try:
                normalized_rows[str(user_key)] = max(0, int(count))
            except (TypeError, ValueError):
                continue
        normalized[str(date_key)] = normalized_rows
    return normalized


def _write_store(data: dict[str, dict[str, int]]) -> None:
    _ensure_parent(USAGE_STORE_PATH)
    USAGE_STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def resolve_user_key(request: Request, email: str | None = None, explicit_user_id: str | None = None) -> str:
    normalized_email = str(email or "").strip().lower()
    if normalized_email:
        return f"email:{normalized_email}"

    explicit = str(explicit_user_id or "").strip()
    if explicit:
        return f"uid:{explicit}"

    cookie_uid = str(request.cookies.get(COOKIE_KEY, "")).strip()
    if cookie_uid:
        return f"cookie:{cookie_uid}"

    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    return f"ipua:{_hash_text(ip + '|' + user_agent)}"


def current_usage_status(user_key: str, *, limit: int = FREE_DAILY_LIMIT, date_key: str | None = None) -> UsageStatus:
    day = date_key or _today_kst()
    with _LOCK:
        store = _read_store()
        used = int(store.get(day, {}).get(user_key, 0))
    remaining = max(0, limit - used)
    return UsageStatus(limit=limit, used=used, remaining=remaining, date=day, blocked=used >= limit)


def consume_usage(user_key: str, *, limit: int = FREE_DAILY_LIMIT, date_key: str | None = None) -> UsageStatus:
    day = date_key or _today_kst()
    with _LOCK:
        store = _read_store()
        day_rows = store.setdefault(day, {})
        used = int(day_rows.get(user_key, 0))
        if used < limit:
            used += 1
            day_rows[user_key] = used
            _write_store(store)
        remaining = max(0, limit - used)
        return UsageStatus(limit=limit, used=used, remaining=remaining, date=day, blocked=used >= limit)


def append_event(*, event_type: str, user_key: str, payload: dict[str, Any] | None = None) -> None:
    record = {
        "at": datetime.now().isoformat(),
        "event_type": str(event_type),
        "user_key": user_key,
        "payload": payload or {},
    }
    _ensure_parent(EVENT_LOG_PATH)
    line = json.dumps(record, ensure_ascii=False)
    with _LOCK:
        with EVENT_LOG_PATH.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
