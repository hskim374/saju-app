"""Lead storage service with Google Sheets backend."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from services.saju_calculator import SajuCalculationError

logger = logging.getLogger(__name__)


def _build_seoul_timezone():
    try:
        return ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        logger.warning("Asia/Seoul zoneinfo not found; falling back to fixed UTC+09:00 offset")
        return timezone(timedelta(hours=9), name="KST")


SEOUL_TZ = _build_seoul_timezone()
SHEET_NAME = "leads"
COLUMNS = [
    "email",
    "name",
    "birth_input",
    "solar_date",
    "year_pillar",
    "month_pillar",
    "day_pillar",
    "time_pillar",
    "created_at",
    "consent",
]


def save_lead(data: dict) -> None:
    """Save lead data using the configured backend."""
    backend = os.getenv("LEAD_STORE_BACKEND", "sheet").lower()
    if backend == "sheet":
        save_lead_to_sheet(data)
        return
    raise SajuCalculationError(f"지원하지 않는 lead 저장 backend입니다: {backend}")


def save_lead_to_sheet(data: dict) -> None:
    """Append a lead row to Google Sheets."""
    try:
        import gspread
    except ImportError as exc:  # pragma: no cover - runtime dependency path
        raise SajuCalculationError("Google Sheets 저장을 위해 gspread 설치가 필요합니다.") from exc

    try:
        client = _build_gspread_client(gspread)
        spreadsheet = client.open_by_key(_required_env("GOOGLE_SHEETS_SPREADSHEET_ID"))
        worksheet = _get_or_create_worksheet(spreadsheet)
        _ensure_header(worksheet)
        worksheet.append_row(_build_row(data), value_input_option="USER_ENTERED")
    except SajuCalculationError:
        raise
    except Exception as exc:
        logger.exception("Failed to save lead to Google Sheets")
        raise SajuCalculationError("Google Sheets 저장에 실패했습니다. 잠시 후 다시 시도해 주세요.") from exc

    logger.info("Lead saved to sheet for %s", data["email"])


def build_lead_payload(*, email: str, name: str | None, consent: bool, result_data: dict) -> dict:
    """Build a DB-like payload that can later map to SQL tables."""
    return {
        "email": email,
        "name": name or "",
        "birth_input": {
            "calendar_type": result_data["raw_input"]["calendar_type"],
            "year": result_data["raw_input"]["year"],
            "month": result_data["raw_input"]["month"],
            "day": result_data["raw_input"]["day"],
            "time_slot": result_data["raw_input"].get("time_slot"),
            "gender": result_data["raw_input"]["gender"],
        },
        "solar_date": result_data["resolved_solar"]["iso"],
        "pillars": {
            "year": result_data["saju"]["year"]["kor"],
            "month": result_data["saju"]["month"]["kor"],
            "day": result_data["saju"]["day"]["kor"],
            "time": result_data["saju"]["time"]["kor"] if result_data["saju"]["time"] else "",
        },
        "created_at": datetime.now(SEOUL_TZ).isoformat(timespec="seconds"),
        "consent": consent,
    }


def _build_gspread_client(gspread_module):
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if service_account_json:
        return gspread_module.service_account_from_dict(json.loads(service_account_json))
    if service_account_file:
        return gspread_module.service_account(filename=service_account_file)
    raise SajuCalculationError("GOOGLE_SERVICE_ACCOUNT_JSON 또는 GOOGLE_SERVICE_ACCOUNT_FILE 환경변수가 필요합니다.")


def _get_or_create_worksheet(spreadsheet):
    try:
        return spreadsheet.worksheet(SHEET_NAME)
    except Exception:
        return spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=len(COLUMNS))


def _ensure_header(worksheet) -> None:
    first_row = worksheet.row_values(1)
    if first_row == COLUMNS:
        return
    if not first_row:
        worksheet.append_row(COLUMNS)


def _build_row(data: dict) -> list[str]:
    return [
        data["email"],
        data["name"],
        json.dumps(data["birth_input"], ensure_ascii=True),
        data["solar_date"],
        data["pillars"]["year"],
        data["pillars"]["month"],
        data["pillars"]["day"],
        data["pillars"]["time"],
        data["created_at"],
        "true" if data["consent"] else "false",
    ]


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SajuCalculationError(f"{name} 환경변수가 필요합니다.")
    return value
