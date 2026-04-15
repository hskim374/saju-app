"""Tests for lightweight main-module UX rules."""

from pathlib import Path
import sys
import types

import pytest

from jinja2 import Environment, FileSystemLoader

from main import _build_pdf_response, _build_result_data, _default_form_data, _today_in_seoul, _validate_gender
from services import premium_report
from services.report_display import build_display_result, localize_text
from services.saju_calculator import SajuCalculationError


def test_default_form_requires_gender_selection():
    form_data = _default_form_data()
    today = _today_in_seoul()

    assert form_data["gender"] == ""
    assert form_data["time_slot"] == ""
    assert form_data["target_year"] == str(today.year)
    assert form_data["target_month"] == str(today.month)
    assert form_data["target_date"] == today.isoformat()


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
    display_result = build_display_result(result_data)
    environment = Environment(loader=FileSystemLoader("templates"))
    html = environment.get_template("report_pdf.html").render(result=display_result)
    template_text = Path("templates/report_pdf.html").read_text(encoding="utf-8")

    assert "사주 분석 리포트" in html
    assert "현재 작동 중인 대운" in html
    assert "프리미엄 사주 리포트" in html
    assert "최종 정리" in html
    assert "오늘의 운세 활용도" in html
    assert "(" in display_result["saju"]["year"]["display"]
    assert "Action Plan" not in html
    assert "@page" in template_text
    assert "margin: 20mm 16mm 20mm 16mm;" in template_text
    assert "grid-template-columns" not in template_text


def test_display_result_formats_pillars_and_stems_in_hangul_hanja():
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

    display_result = build_display_result(result_data)

    assert display_result["saju"]["year"]["display"].endswith(")")
    assert "(" in display_result["saju"]["day"]["display"]
    assert "(" in display_result["daewoon"]["active_cycle_summary"]["pillar_display"]
    assert "(" in display_result["daily_fortune"]["pillar_display"]
    assert display_result["daily_fortune"]["score"]["title"] == "오늘의 운세 활용도"
    assert "Action Plan" not in display_result["premium_report"]["sections"][-1]["title"]


def test_pillar_sections_do_not_expose_raw_english_yinyang_or_elements():
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

    display_result = build_display_result(result_data)
    pillar_sections = display_result["interpretation_sections"]["pillars"]

    joined = " ".join(
        item
        for key in ["year", "month", "day", "time"]
        for field in ["one_line", "highlight"]
        for item in ([pillar_sections[key][field]] if pillar_sections.get(key) else [])
    )
    joined += " " + " ".join(
        item
        for key in ["year", "month", "day", "time"]
        if pillar_sections.get(key)
        for field in ["easy_explanation", "real_life", "strength_and_risk", "action_advice"]
        for item in pillar_sections[key][field]
    )

    for raw in ["yang", "yin", "wood", "fire", "earth", "metal", "water"]:
        assert raw not in joined
    assert "양(陽)" in joined or "음(陰)" in joined
    assert any(label in joined for label in ["목(木)", "화(火)", "토(土)", "금(金)", "수(水)"])


def test_pillar_sections_do_not_expose_raw_english_role_names():
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

    display_result = build_display_result(result_data)
    pillar_sections = display_result["interpretation_sections"]["pillars"]
    joined = " ".join(
        item
        for key in ["year", "month", "day", "time"]
        if pillar_sections.get(key)
        for field in ["one_line", "highlight", "title"]
        for item in ([pillar_sections[key][field]] if isinstance(pillar_sections[key][field], str) else [])
    )
    joined += " " + " ".join(
        item
        for key in ["year", "month", "day", "time"]
        if pillar_sections.get(key)
        for field in ["easy_explanation", "real_life", "strength_and_risk", "action_advice"]
        for item in pillar_sections[key][field]
    )

    for raw in ["month", "day", "time", "year"]:
        assert raw not in joined
    assert any(label in joined for label in ["월주 자리", "일주 자리", "시주 자리", "년주 자리"])


def test_localize_text_does_not_inject_pillar_labels_into_normal_words():
    text = "결론을 빠르게 정해야 하는 장면에서는 일간 기준을 먼저 확인합니다."
    localized = localize_text(text)

    assert "정해(丁亥)야" not in localized
    assert "기(己)준" not in localized
    assert localized == text


def test_localize_text_does_not_inject_pillar_labels_into_space_separated_verbs():
    text = "일정 상한선과 관계 경계를 숫자로 정해 두는 것이 도움이 됩니다."
    localized = localize_text(text)

    assert "정해(丁亥) 두는" not in localized
    assert localized == text


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
    assert "quarterly_fortune" not in result_data
    assert result_data["summary_card"]["year_trend"]
    assert result_data["summary_card"]["wealth"]
    assert result_data["analysis_context"]["strength"]["display_label"]
    assert result_data["analysis_context"]["yongshin"]["display"]["primary"]
    assert result_data["analysis_context"]["yongshin"]["confidence_display"]
    assert "natal" in result_data["analysis_context"]["interactions"]
    assert result_data["analysis_context"]["structure"]["signature_key"]
    assert result_data["interpretation_signals"]["core"]
    assert result_data["structured_report"]["headline"]
    assert result_data["structured_report"]["sections"]["core_structure"]
    assert result_data["structured_report"]["match_logs"]["career"]["matched_count"] >= 0
    assert isinstance(result_data["structured_report"]["match_logs"]["career"]["matched_ids"], list)
    assert result_data["analysis_context"]["special_stars"]["summary"]
    assert result_data["analysis_context"]["uncertainty_notes"]
    assert result_data["saju_id"]
    assert result_data["raw_input"]["saju_id"] == result_data["saju_id"]
    assert result_data["cache_key"]


def test_result_template_renders_balance_analysis_card():
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

    display_result = build_display_result(result_data)
    environment = Environment(loader=FileSystemLoader("templates"))
    html = environment.get_template("result.html").render(
        result=display_result,
        premium_upgrade_link="/premium",
        email_form_data={"email": "", "name": "", "consent": False},
        email_success_message=None,
        email_error_message=None,
    )

    assert "균형 해석" in html
    assert "용신 확신도" in html
    assert "근거 보기" in html
    assert "신강/신약 점수" in html
    assert "신살 흐름" in html
    assert "해석 유의점" in html
    assert display_result["daily_fortune"]["score"]["driver_line"] in html
    assert display_result["daily_fortune"]["score"]["guide_lines"][0] in html
    assert "점수 근거 Top" in html
    assert display_result["weekly_fortune"][0]["reason_tag"] in html
    assert display_result["main_cards"]["personality"]["one_line"]
    assert display_result["main_cards"]["career"]["source"] in {"structured", "legacy"}
    assert display_result["weekly_fortune"][0]["factor_top_compact"] in html
    assert display_result["weekly_fortune"][0]["confidence_label"] in html
    assert display_result["weekly_fortune"][0]["driver_line"] in html
    assert display_result["analysis_context"]["yongshin"]["display"]["primary"] in html
    assert "핵심 근거" in html
    assert "구조 판별 요약" in html
    assert display_result["structured_report"]["headline"] in html
    assert display_result["premium_report"]["analysis_brief"]["brief"][0] in html


def test_daily_fortune_score_matches_first_weekly_card_for_same_date():
    _, result_data = _build_result_data(
        calendar_type="solar",
        year=2011,
        month=4,
        day=7,
        time_slot="jin",
        is_leap_month=False,
        gender="male",
        target_year="2026",
        target_month="4",
        target_date="2026-04-10",
    )

    daily_score = result_data["daily_fortune"]["score"]
    weekly_first = result_data["weekly_fortune"][0]

    assert result_data["daily_fortune"]["date"] == weekly_first["date"]
    assert daily_score["value"] == weekly_first["score"]
    assert daily_score["grade"] == weekly_first["grade"]
    assert daily_score["label"] == weekly_first["label"]
    assert daily_score["reason_tag"] == weekly_first["reason_tag"]
    assert daily_score["caution_tag"] == weekly_first["caution_tag"]


def test_daily_and_weekly_scores_match_for_1973_case_with_gendered_daewoon():
    _, result_data = _build_result_data(
        calendar_type="solar",
        year=1973,
        month=6,
        day=6,
        time_slot="sul",
        is_leap_month=False,
        gender="male",
        target_year="2026",
        target_month="4",
        target_date="2026-04-10",
    )

    daily_score = result_data["daily_fortune"]["score"]
    weekly_first = result_data["weekly_fortune"][0]

    assert result_data["daily_fortune"]["date"] == weekly_first["date"] == "2026-04-10"
    assert daily_score["value"] == weekly_first["score"]
    assert daily_score["grade"] == weekly_first["grade"]
    assert daily_score["label"] == weekly_first["label"]
    assert daily_score["reason_tag"] == weekly_first["reason_tag"]
    assert daily_score["caution_tag"] == weekly_first["caution_tag"]


def test_premium_sentence_pools_have_expected_unique_sentences_per_type():
    expected_types = {"stable", "drive", "change", "relation", "chance"}

    assert set(premium_report.action_intro_pool) == expected_types
    assert set(premium_report.final_summary_pool) == expected_types

    for user_type in expected_types:
        assert len(premium_report.action_intro_pool[user_type]) >= 40
        assert len(set(premium_report.action_intro_pool[user_type])) == len(premium_report.action_intro_pool[user_type])
        assert len(premium_report.final_summary_pool[user_type]) == 50
        assert len(set(premium_report.final_summary_pool[user_type])) == 50


def test_premium_action_plan_pools_are_expanded_beyond_base_pairs():
    assert len(premium_report.ACTION_FORCE_TEMPLATES) >= 24

    for pool in [
        premium_report.ACTION_PLAN_DAY_STEM_LINES,
        premium_report.ACTION_PLAN_MONTH_BRANCH_LINES,
        premium_report.ACTION_PLAN_DOMINANT_LINES,
        premium_report.ACTION_PLAN_WEAK_LINES,
        premium_report.ACTION_PLAN_MONTH_TEN_GOD_LINES,
        premium_report.ACTION_PLAN_DAEWOON_LINES,
        premium_report.ACTION_PLAN_YEAR_FLOW_LINES,
        premium_report.ACTION_PLAN_CAREER_LINES,
        premium_report.ACTION_PLAN_RELATION_LINES,
    ]:
        for options in pool.values():
            assert len(options) >= 8
            assert len(set(options)) == len(options)


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


def test_premium_action_plan_changes_for_different_charts(monkeypatch):
    monkeypatch.setattr(premium_report.random, "choice", lambda seq: seq[0])

    _, first = _build_result_data(
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
    _, second = _build_result_data(
        calendar_type="solar",
        year=1973,
        month=6,
        day=6,
        time_slot="sul",
        is_leap_month=False,
        gender="female",
        target_year="2026",
        target_month="3",
        target_date="2026-03-31",
    )

    first_action = next(section for section in first["premium_report"]["sections"] if section["key"] == "action_plan")
    second_action = next(section for section in second["premium_report"]["sections"] if section["key"] == "action_plan")

    assert first_action["summary_lines"] != second_action["summary_lines"]
    assert first_action["patterns"] != second_action["patterns"]
    assert first_action["action_points"] != second_action["action_points"]
    assert len(first_action["action_points"]) == 4
    assert len(set(first_action["action_points"])) == 4
    assert all(point.strip() for point in first_action["action_points"])


def test_premium_core_sections_have_unique_patterns_and_actions():
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

    sections = {section["key"]: section for section in result_data["premium_report"]["sections"]}
    for key in ["timeline", "decision_points", "wealth_deep", "career_direction", "relationship_deep", "risk_analysis"]:
        section = sections[key]
        assert section["headline"].strip()
        assert len(section["summary_lines"]) >= 3
        assert all(line.strip() for line in section["summary_lines"])
        assert len(set(section["summary_lines"])) == len(section["summary_lines"])
        assert len(section["patterns"]) >= 3
        assert len(set(section["patterns"])) == len(section["patterns"])
        assert len(section["action_points"]) >= 3
        assert len(set(section["action_points"])) == len(section["action_points"])
        assert section["strength"].strip()
        assert section["risk"].strip()
        assert section["action_note"].strip()
        assert len({section["strength"], section["risk"], section["action_note"]}) >= 2

    action_plan = sections["action_plan"]
    assert action_plan["headline"].strip()
    assert len(action_plan["summary_lines"]) == 4
    assert all(line.strip() for line in action_plan["summary_lines"])
    assert len(set(action_plan["summary_lines"])) == 4


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
