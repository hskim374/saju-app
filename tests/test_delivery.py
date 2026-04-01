"""Tests for email delivery and lead storage services."""

from __future__ import annotations

from datetime import datetime
import json
import sys
import types
from zoneinfo import ZoneInfo

import pytest

from main import (
    _build_report_view_link,
    _build_result_data,
    _check_email_rate_limit,
    _mark_email_rate_limit,
    _validate_email,
)
from services.email_sender import send_report_email
from services.lead_store import build_lead_payload, save_lead_to_sheet
from services.saju_calculator import SajuCalculationError


def _sample_result_data():
    _, result = _build_result_data(
        calendar_type="solar",
        year=2006,
        month=8,
        day=1,
        time_slot="mi",
        is_leap_month=False,
        gender="male",
        target_year="2026",
        target_month="3",
        target_date="2026-03-31",
    )
    return result


def test_validate_email_accepts_normalized_address():
    assert _validate_email("TEST@example.com ") == "test@example.com"
    with pytest.raises(SajuCalculationError):
        _validate_email("not-an-email")


def test_rate_limit_blocks_same_request_twice():
    _check_email_rate_limit("user@example.com", "sample")
    _mark_email_rate_limit("user@example.com", "sample")
    with pytest.raises(SajuCalculationError):
        _check_email_rate_limit("user@example.com", "sample")


def test_build_report_view_link_contains_query_values():
    result = _sample_result_data()
    request = types.SimpleNamespace(base_url="http://testserver/")

    link = _build_report_view_link(request, result)

    assert link.startswith("http://testserver/report/view?")
    assert "calendar_type=solar" in link
    assert "gender=male" in link


def test_send_report_email_uses_html_template(monkeypatch):
    result = _sample_result_data()
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            captured["host"] = host
            captured["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            captured["tls"] = True

        def login(self, username, password):
            captured["username"] = username
            captured["password"] = password

        def send_message(self, message):
            captured["message"] = message

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SMTP_FROM_NAME", "saju-mvp")
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)

    send_report_email(
        to_email="user@example.com",
        name="테스터",
        result_data=result,
        detail_link="http://testserver/report/view?sample=1",
    )

    assert captured["host"] == "smtp.example.com"
    assert captured["message"]["To"] == "user@example.com"
    html_part = captured["message"].get_payload()[1]
    html_body = html_part.get_content()
    assert "사주 리포트" in html_body
    assert "대운 흐름" in html_body
    assert "오행 · 십성" in html_body
    assert "직장운" in html_body
    assert "결혼운 / 연애운" in html_body
    assert "계산 기준" in html_body
    assert "웹에서 상세보기" in html_body


def test_build_lead_payload_matches_sheet_shape():
    result = _sample_result_data()
    lead = build_lead_payload(
        email="user@example.com",
        name="홍길동",
        consent=True,
        result_data=result,
    )

    assert lead["email"] == "user@example.com"
    assert lead["birth_input"]["time_slot"] == "mi"
    assert lead["pillars"]["year"] == result["saju"]["year"]["kor"]
    created_at = datetime.fromisoformat(lead["created_at"])
    assert created_at.utcoffset().total_seconds() == 9 * 3600
    assert lead["consent"] is True


def test_save_lead_to_sheet_appends_row(monkeypatch):
    appended_rows = []

    class FakeWorksheet:
        def __init__(self):
            self.first_row = []

        def row_values(self, idx):
            return self.first_row

        def append_row(self, row, value_input_option=None):
            appended_rows.append((row, value_input_option))
            if not self.first_row:
                self.first_row = row

    class FakeSpreadsheet:
        def __init__(self):
            self.worksheet_obj = FakeWorksheet()

        def worksheet(self, title):
            return self.worksheet_obj

        def add_worksheet(self, title, rows, cols):
            return self.worksheet_obj

    class FakeClient:
        def __init__(self):
            self.spreadsheet = FakeSpreadsheet()

        def open_by_key(self, key):
            return self.spreadsheet

    fake_gspread = types.SimpleNamespace(
        service_account=lambda filename=None: FakeClient(),
        service_account_from_dict=lambda info: FakeClient(),
    )
    monkeypatch.setitem(sys.modules, "gspread", fake_gspread)
    monkeypatch.setenv("GOOGLE_SHEETS_SPREADSHEET_ID", "sheet-id")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", json.dumps({"type": "service_account"}))

    save_lead_to_sheet(
        {
            "email": "user@example.com",
            "name": "홍길동",
            "birth_input": {"year": 2006},
            "solar_date": "2006-08-01",
            "pillars": {"year": "병술", "month": "을미", "day": "임술", "time": "정미"},
            "created_at": "2026-04-01T09:00:00+09:00",
            "consent": True,
        }
    )

    assert len(appended_rows) == 2
    assert appended_rows[1][0][0] == "user@example.com"
    assert appended_rows[1][1] == "USER_ENTERED"
