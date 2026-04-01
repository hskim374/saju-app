"""Tests for daewoon and fortune-layer services."""

from datetime import date

from services.career_fortune import build_career_fortune
from services.daily_fortune import calculate_daily_fortune
from services.daewoon import calculate_daewoon
from services.monthly_fortune import calculate_monthly_fortune
from services.relationship_fortune import build_relationship_fortune
from services.saju_calculator import get_basic_saju_result
from services.summary_card import build_summary_card
from services.yearly_fortune import calculate_yearly_fortune


def test_daewoon_direction_and_cycle_count_for_male_case():
    saju_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    daewoon = calculate_daewoon(saju_result, gender="male")

    assert daewoon["direction"] == "forward"
    assert daewoon["start_age"] >= 1
    assert daewoon["start_age_display"]
    assert len(daewoon["cycles"]) == 8
    assert daewoon["cycles"][0]["pillar"] != saju_result["saju"]["month"]["kor"]
    assert daewoon["cycles"][0]["summary"]
    assert daewoon["cycles"][0]["explanation"]
    assert daewoon["cycles"][0]["advice"]
    assert len(daewoon["cycles"][0]["keywords"]) == 3
    assert daewoon["active_cycle_summary"]["summary"]
    assert daewoon["active_cycle_summary"]["explanation"]
    assert daewoon["active_cycle_summary"]["advice"]
    assert daewoon["active_cycle_summary"]["pillar"]


def test_daewoon_direction_and_result_are_deterministic_for_female_case():
    saju_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)

    first = calculate_daewoon(saju_result, gender="female")
    second = calculate_daewoon(saju_result, gender="female")

    assert first == second
    assert first["direction"] == "reverse"


def test_daewoon_cycle_interpretations_change_with_pillar_flow():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    daewoon = calculate_daewoon(saju_result, gender="female")

    summaries = [cycle["summary"] for cycle in daewoon["cycles"][:3]]

    assert len(set(summaries)) == 3
    assert all(cycle["ten_god"] for cycle in daewoon["cycles"][:3])


def test_yearly_fortune_returns_expected_2026_pillar():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    daewoon = calculate_daewoon(saju_result, gender="male")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)

    assert year_fortune["year"] == 2026
    assert year_fortune["pillar"] == "병오"
    assert len(year_fortune["focus"]) == 3
    assert year_fortune["headline"]
    assert year_fortune["explanation"]
    assert year_fortune["advice"]
    assert year_fortune["section"]["highlight"]
    assert year_fortune["section"]["real_life"]
    assert year_fortune["section"]["strength_and_risk"]


def test_monthly_fortune_returns_twelve_months_with_pillars():
    saju_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    monthly = calculate_monthly_fortune(saju_result, 2026)

    assert len(monthly) == 12
    assert monthly[0]["month"] == 1
    assert monthly[-1]["month"] == 12
    assert len({item["pillar"] for item in monthly}) >= 10
    assert len({item["summary"] for item in monthly}) == 12
    assert all(item["headline"] for item in monthly)
    assert all(item["explanation"] for item in monthly)
    assert all(item["advice"] for item in monthly)


def test_daily_fortune_is_deterministic_for_specific_date():
    saju_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)

    first = calculate_daily_fortune(saju_result, date(2026, 3, 31))
    second = calculate_daily_fortune(saju_result, date(2026, 3, 31))

    assert first == second
    assert first["date"] == "2026-03-31"
    assert first["pillar"]
    assert first["headline"]
    assert first["explanation"]
    assert first["advice"]
    assert first["section"]["highlight"]
    assert first["section"]["real_life"]
    assert first["section"]["strength_and_risk"]
    assert len(first["keywords"]) == 3


def test_career_and_relationship_fortunes_return_expected_structure():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    daewoon = calculate_daewoon(saju_result, gender="female")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)

    career = build_career_fortune(saju_result, year_fortune)
    relationship = build_relationship_fortune("female", year_fortune)

    assert career["summary"]
    assert career["headline"]
    assert career["explanation"]
    assert career["advice"]
    assert career["section"]["highlight"]
    assert career["section"]["real_life"]
    assert career["section"]["strength_and_risk"]
    assert career["trend"]
    assert career["intensity"]
    assert career["tone_kor"]
    assert career["intensity_kor"]
    assert career["strengths"]
    assert career["warnings"]
    assert relationship["summary"]
    assert relationship["headline"]
    assert relationship["explanation"]
    assert relationship["advice"]
    assert relationship["section"]["highlight"]
    assert relationship["section"]["real_life"]
    assert relationship["section"]["strength_and_risk"]
    assert relationship["trend"]
    assert relationship["intensity"]
    assert relationship["intensity_kor"]
    assert relationship["strengths"]
    assert relationship["warnings"]


def test_summary_card_returns_short_labels():
    saju_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    daewoon = calculate_daewoon(saju_result, gender="male")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)
    career = build_career_fortune(saju_result, year_fortune)
    relationship = build_relationship_fortune("male", year_fortune)
    summary_card = build_summary_card(
        {"dominant": ["earth"], "weak": ["metal"]},
        year_fortune,
        career,
        relationship,
    )

    assert summary_card["year_trend"]
    assert summary_card["year_trend"] == "기회 활용 + 재물 관리 병행"
    assert summary_card["wealth"] == "벌기보다 쌓는 전략"
    assert summary_card["career"] == "성과와 관리 병행"
    assert summary_card["relationship"] == "인연 유입, 속도 조절 필요"
