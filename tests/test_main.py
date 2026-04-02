"""Tests for lightweight main-module UX rules."""

from pathlib import Path
import sys
import types

import pytest

from jinja2 import Environment, FileSystemLoader

from main import _build_pdf_response, _build_result_data, _default_form_data, _validate_gender
from services import premium_report
from services.saju_calculator import SajuCalculationError


def test_default_form_requires_gender_selection():
    form_data = _default_form_data()

    assert form_data["gender"] == ""
    assert form_data["time_slot"] == ""


def test_validate_gender_rejects_missing_or_unknown_values():
    with pytest.raises(SajuCalculationError):
        _validate_gender(None)

    with pytest.raises(SajuCalculationError):
        _validate_gender("unknown")

    assert _validate_gender("male") == "male"
    assert _validate_gender("female") == "female"


def test_pdf_template_is_separated_and_renders_document_layout():
    _, result_data = _build_result_data(
        calendar_type="solar",
        year=2006,
        month=8,
        day=1,
        time_slot="sa",
        is_leap_month=False,
        gender="male",
        target_year="2026",
        target_month="3",
        target_date="2026-03-31",
        premium="1",
    )
    environment = Environment(loader=FileSystemLoader("templates"))
    html = environment.get_template("report_pdf.html").render(result=result_data)
    template_text = Path("templates/report_pdf.html").read_text(encoding="utf-8")

    assert "사주 분석 리포트" in html
    assert "현재 작동 중인 대운" in html
    assert "프리미엄 사주 리포트" in html
    assert "최종 정리" in html
    assert "@page" in template_text
    assert "margin: 20mm 16mm 20mm 16mm;" in template_text
    assert "grid-template-columns" not in template_text


def test_result_data_contains_premium_report_structure():
    _, result_data = _build_result_data(
        calendar_type="solar",
        year=2006,
        month=8,
        day=1,
        time_slot="sa",
        is_leap_month=False,
        gender="male",
        target_year="2026",
        target_month="3",
        target_date="2026-03-31",
    )

    assert result_data["premium_report"]["enabled"] is False
    assert result_data["premium_report"]["header"] == "프리미엄 사주 리포트"
    assert result_data["premium_report"]["user_type"] == "chance"
    assert len(result_data["premium_report"]["overview"]) == 3
    assert len(result_data["premium_report"]["teaser_items"]) >= 3
    assert len(result_data["premium_report"]["sections"]) == 7
    assert result_data["premium_report"]["sections"][0]["core_insight"]
    assert result_data["premium_report"]["final_summary"]["headline"] == "최종 정리"


def test_premium_sentence_pools_have_20_unique_sentences_per_type():
    expected_types = {"stable", "drive", "change", "relation", "chance"}

    assert set(premium_report.action_intro_pool) == expected_types
    assert set(premium_report.final_summary_pool) == expected_types

    for user_type in expected_types:
        assert len(premium_report.action_intro_pool[user_type]) == 20
        assert len(set(premium_report.action_intro_pool[user_type])) == 20
        assert len(premium_report.final_summary_pool[user_type]) == 20
        assert len(set(premium_report.final_summary_pool[user_type])) == 20


def test_day_stem_maps_to_expected_user_type():
    assert premium_report.map_day_stem_to_user_type("갑") == "stable"
    assert premium_report.map_day_stem_to_user_type("을") == "stable"
    assert premium_report.map_day_stem_to_user_type("병") == "drive"
    assert premium_report.map_day_stem_to_user_type("정") == "drive"
    assert premium_report.map_day_stem_to_user_type("무") == "change"
    assert premium_report.map_day_stem_to_user_type("기") == "change"
    assert premium_report.map_day_stem_to_user_type("경") == "relation"
    assert premium_report.map_day_stem_to_user_type("신") == "relation"
    assert premium_report.map_day_stem_to_user_type("임") == "chance"
    assert premium_report.map_day_stem_to_user_type("계") == "chance"


def test_premium_random_sentences_are_selected_from_type_pool(monkeypatch):
    monkeypatch.setattr(premium_report.random, "choice", lambda seq: seq[-1])

    _, result_data = _build_result_data(
        calendar_type="solar",
        year=2006,
        month=8,
        day=1,
        time_slot="sa",
        is_leap_month=False,
        gender="male",
        target_year="2026",
        target_month="3",
        target_date="2026-03-31",
    )

    user_type = result_data["premium_report"]["user_type"]
    action_plan = next(section for section in result_data["premium_report"]["sections"] if section["key"] == "action_plan")

    assert action_plan["summary_lines"][0] == premium_report.action_intro_pool[user_type][-1]
    assert result_data["premium_report"]["final_summary"]["text"] == premium_report.final_summary_pool[user_type][-1]


def test_premium_report_explains_jargon_in_plain_korean():
    _, result_data = _build_result_data(
        calendar_type="solar",
        year=2006,
        month=8,
        day=1,
        time_slot="sa",
        is_leap_month=False,
        gender="male",
        target_year="2026",
        target_month="3",
        target_date="2026-03-31",
    )

    timeline_lines = result_data["premium_report"]["sections"][0]["summary_lines"]
    decision_lines = result_data["premium_report"]["sections"][1]["summary_lines"]

    assert any("현재 10년 운의 이름은" in line for line in timeline_lines)
    assert any("쉽게 말하면" in line for line in timeline_lines + decision_lines)


def test_pdf_response_returns_downloadable_application_pdf(monkeypatch):
    _, result_data = _build_result_data(
        calendar_type="solar",
        year=2006,
        month=8,
        day=1,
        time_slot="sa",
        is_leap_month=False,
        gender="male",
        target_year="2026",
        target_month="3",
        target_date="2026-03-31",
        premium="1",
    )

    class FakeHTML:
        def __init__(self, string, base_url):
            self.string = string
            self.base_url = base_url

        def write_pdf(self):
            return b"%PDF-test"

    fake_module = types.SimpleNamespace(HTML=FakeHTML)
    monkeypatch.setitem(sys.modules, "weasyprint", fake_module)

    request = types.SimpleNamespace(base_url="http://testserver/")
    response = _build_pdf_response(request, result_data)

    assert response.media_type == "application/pdf"
    expected_filename = f'attachment; filename="saju-report-{result_data["report_generated_on"].replace("-", "")}.pdf"'
    assert response.headers["Content-Disposition"] == expected_filename
    assert response.body == b"%PDF-test"


def test_pdf_response_requires_premium_report():
    _, result_data = _build_result_data(
        calendar_type="solar",
        year=2006,
        month=8,
        day=1,
        time_slot="sa",
        is_leap_month=False,
        gender="male",
        target_year="2026",
        target_month="3",
        target_date="2026-03-31",
    )

    request = types.SimpleNamespace(base_url="http://testserver/")

    with pytest.raises(SajuCalculationError):
        _build_pdf_response(request, result_data)
