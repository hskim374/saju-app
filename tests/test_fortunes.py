"""Tests for daewoon and fortune-layer services."""

from datetime import date

from data.month_ten_god_specialized import MONTH_TEN_GOD_CAREER_LINES, MONTH_TEN_GOD_RELATION_LINES
import services.summary_card as summary_card_module
from services.career_fortune import build_career_fortune
import services.daily_fortune as daily_fortune_module
from services.daily_fortune import calculate_daily_fortune
from services.daewoon import calculate_daewoon
from services.monthly_fortune import calculate_monthly_fortune
from services.relationship_fortune import build_relationship_fortune
from services.saju_calculator import get_basic_saju_result
from services.summary_card import build_summary_card
import services.weekly_fortune as weekly_fortune_module
from services.weekly_fortune import build_weekly_fortune
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
    assert first["score"]["title"] == "오늘의 운세 활용도"
    assert 1 <= first["score"]["value"] <= 100
    assert first["score"]["grade"]
    assert first["score"]["label"]
    assert first["score"]["summary"]
    assert len(first["score"]["factors"]) >= 5


def test_daily_fortune_sentence_pools_are_significantly_expanded():
    day_stem_headline_total = sum(
        len(daily_fortune_module._day_stem_headline_options(stem))
        for stem in ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    )
    month_branch_headline_total = sum(
        len(daily_fortune_module._month_branch_headline_options(branch))
        for branch in ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    )
    action_total = sum(
        len(daily_fortune_module._day_stem_action_options(stem))
        for stem in ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    )
    action_total += sum(
        len(daily_fortune_module._month_branch_action_options(branch))
        for branch in ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    )
    action_total += sum(
        len(daily_fortune_module._time_branch_action_options(branch, ["기회", "정리", "실행"]))
        for branch in ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    )

    assert day_stem_headline_total >= 60
    assert month_branch_headline_total >= 60
    assert action_total >= 170
    assert len(daily_fortune_module._profile_headline_options("planner")) >= 5
    assert len(daily_fortune_module._profile_explanation_options("planner")) >= 5
    assert len(daily_fortune_module._profile_advice_options("planner")) >= 5


def test_daily_score_can_reach_top_and_defense_grades():
    top_score = daily_fortune_module._build_daily_score(
        ten_god="정재",
        daily_profile="stabilizer",
        month_branch="축",
        time_branch="축",
        keywords=["축적", "관리", "실무"],
    )
    low_score = daily_fortune_module._build_daily_score(
        ten_god="겁재",
        daily_profile="driver",
        month_branch="사",
        time_branch="사",
        keywords=["주의", "경쟁", "분산"],
    )

    assert top_score["value"] == 99
    assert top_score["grade"] == "S"
    assert low_score["value"] == 9
    assert low_score["grade"] == "D"


def test_daily_action_advice_uses_score_based_execution_language():
    high_lines = daily_fortune_module._daily_execution_action_lines(
        score=99,
        ten_god="정재",
        keywords=["축적", "관리", "실무"],
        seed=1,
    )
    low_lines = daily_fortune_module._daily_execution_action_lines(
        score=9,
        ten_god="겁재",
        keywords=["주의", "경쟁", "분산"],
        seed=1,
    )
    joined = " ".join([*high_lines, *low_lines])

    assert len(high_lines) == 3
    assert len(low_lines) == 3
    assert all(len(line) <= 35 for line in [*high_lines, *low_lines])
    assert not any(term in joined for term in ["일간", "월지", "시지"])
    assert any(word in " ".join(high_lines) for word in ["확정", "제안", "마감", "실행", "성과"])
    assert any(word in " ".join(low_lines) for word in ["휴식", "내일", "줄이세요", "피하고", "무리"])


def test_daily_action_advice_pools_are_doubled_without_duplicates():
    score_total = sum(len(pool) for pool in daily_fortune_module.ACTION_BY_SCORE_BUCKET.values())
    ten_god_total = sum(len(pool) for pool in daily_fortune_module.ACTION_BY_TEN_GOD.values())
    keyword_total = sum(len(pool) for pool in daily_fortune_module.ACTION_BY_KEYWORD.values())
    all_lines = [
        line
        for data in [
            daily_fortune_module.ACTION_BY_SCORE_BUCKET,
            daily_fortune_module.ACTION_BY_TEN_GOD,
            daily_fortune_module.ACTION_BY_KEYWORD,
        ]
        for pool in data.values()
        for line in pool
    ]

    assert score_total == 72
    assert ten_god_total == 60
    assert keyword_total == 112
    assert len(all_lines) == 244
    assert len(set(all_lines)) == 244
    assert all(len(line) <= 35 for line in all_lines)


def test_weekly_fortune_returns_seven_score_cards_from_start_date():
    saju_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)

    weekly = build_weekly_fortune(saju_result, date(2026, 4, 8))

    assert len(weekly) == 7
    assert weekly[0]["date"] == "2026-04-08"
    assert weekly[-1]["date"] == "2026-04-14"
    assert weekly[0]["is_today"] is True
    assert all(item["score"] for item in weekly)
    assert all(item["grade"] for item in weekly)
    assert all(item["label"] for item in weekly)
    assert all(item["summary"] for item in weekly)
    assert all(len(item["summary"]) <= 20 for item in weekly)
    assert len({item["date"] for item in weekly}) == 7


def test_weekly_fortune_short_summary_pool_has_very_high_bucket():
    summary_count = sum(len(pool) for pool in weekly_fortune_module.SHORT_SUMMARY_POOLS.values())

    assert summary_count == 144
    assert len(weekly_fortune_module.SHORT_SUMMARY_POOLS["very_high"]) == 24
    assert weekly_fortune_module._summary_bucket(90) == "very_high"
    assert weekly_fortune_module._summary_bucket(89) == "high"
    assert weekly_fortune_module._score_class(90) == "score-very-high"
    assert all(
        len(set(pool)) == len(pool)
        for pool in weekly_fortune_module.SHORT_SUMMARY_POOLS.values()
    )
    assert all(
        len(summary) <= 20
        for pool in weekly_fortune_module.SHORT_SUMMARY_POOLS.values()
        for summary in pool
    )


def test_career_and_relationship_fortunes_return_expected_structure():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    daewoon = calculate_daewoon(saju_result, gender="female")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)

    career = build_career_fortune(saju_result, year_fortune)
    relationship = build_relationship_fortune("female", year_fortune, saju_result)

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


def test_daily_fortune_changes_with_same_date_for_different_natal_charts():
    first_chart = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    second_chart = get_basic_saju_result("solar", 1988, 5, 19, 18, 0)

    first_daily = calculate_daily_fortune(first_chart, date(2026, 3, 31))
    second_daily = calculate_daily_fortune(second_chart, date(2026, 3, 31))

    assert first_daily["headline"] != second_daily["headline"]
    assert first_daily["section"]["easy_explanation"] != second_daily["section"]["easy_explanation"]
    assert first_daily["section"]["real_life"] != second_daily["section"]["real_life"]
    assert first_daily["section"]["strength_and_risk"] != second_daily["section"]["strength_and_risk"]
    assert first_daily["section"]["action_advice"] != second_daily["section"]["action_advice"]
    assert first_daily["score"] != second_daily["score"]


def test_daily_fortune_avoids_repeating_natal_day_prefix_in_real_life():
    saju_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    daily = calculate_daily_fortune(saju_result, date(2026, 4, 3))

    first_real = daily["section"]["real_life"][0]

    assert "임술 일주 기준으로 보면 임술 일주 기준으로 보면" not in first_real
    assert "원국 일주 임술" in first_real


def test_career_and_relationship_reflect_natal_chart_not_only_current_flow():
    first_chart = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    second_chart = get_basic_saju_result("solar", 1988, 5, 19, 18, 0)

    first_daewoon = calculate_daewoon(first_chart, gender="male")
    second_daewoon = calculate_daewoon(second_chart, gender="male")
    first_year = calculate_yearly_fortune(first_chart, first_daewoon, 2026)
    second_year = calculate_yearly_fortune(second_chart, second_daewoon, 2026)

    first_career = build_career_fortune(first_chart, first_year)
    second_career = build_career_fortune(second_chart, second_year)
    first_relationship = build_relationship_fortune("male", first_year, first_chart)
    second_relationship = build_relationship_fortune("male", second_year, second_chart)

    assert first_career["headline"] != second_career["headline"]
    assert first_career["section"]["easy_explanation"] != second_career["section"]["easy_explanation"]
    assert first_career["section"]["real_life"] != second_career["section"]["real_life"]
    assert first_relationship["headline"] != second_relationship["headline"]
    assert first_relationship["section"]["easy_explanation"] != second_relationship["section"]["easy_explanation"]
    assert first_relationship["section"]["real_life"] != second_relationship["section"]["real_life"]


def test_day_pillar_and_month_ten_god_layers_are_visible_in_fortunes():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    daewoon = calculate_daewoon(saju_result, gender="female")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)
    daily = calculate_daily_fortune(saju_result, date(2026, 3, 31))
    career = build_career_fortune(saju_result, year_fortune)
    relationship = build_relationship_fortune("female", year_fortune, saju_result)

    day_kor = saju_result["saju"]["day"]["kor"]
    month_ten_god = "정관"

    assert day_kor in daily["summary"]
    assert day_kor in career["headline"]
    assert day_kor in relationship["headline"]
    assert any(month_ten_god in line for line in career["section"]["easy_explanation"])
    assert any(month_ten_god in line for line in relationship["section"]["easy_explanation"])
    assert any(line in " ".join(career["section"]["easy_explanation"]) for line in MONTH_TEN_GOD_CAREER_LINES[month_ten_god])
    assert any(line in " ".join(relationship["section"]["easy_explanation"]) for line in MONTH_TEN_GOD_RELATION_LINES[month_ten_god])


def test_daily_career_and_relationship_sections_have_expanded_line_volume():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    daewoon = calculate_daewoon(saju_result, gender="female")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)
    daily = calculate_daily_fortune(saju_result, date(2026, 3, 31))
    career = build_career_fortune(saju_result, year_fortune)
    relationship = build_relationship_fortune("female", year_fortune, saju_result)

    assert len(daily["section"]["easy_explanation"]) >= 5
    assert len(daily["section"]["real_life"]) >= 6
    assert len(daily["section"]["strength_and_risk"]) >= 5
    assert len(daily["section"]["action_advice"]) >= 3
    assert len(career["section"]["easy_explanation"]) >= 5
    assert len(career["section"]["real_life"]) >= 6
    assert len(career["section"]["strength_and_risk"]) >= 5
    assert len(career["section"]["action_advice"]) >= 3
    assert len(relationship["section"]["easy_explanation"]) >= 5
    assert len(relationship["section"]["real_life"]) >= 6
    assert len(relationship["section"]["strength_and_risk"]) >= 5
    assert len(relationship["section"]["action_advice"]) >= 3


def test_summary_card_returns_short_labels():
    saju_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    daewoon = calculate_daewoon(saju_result, gender="male")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)
    career = build_career_fortune(saju_result, year_fortune)
    relationship = build_relationship_fortune("male", year_fortune, saju_result)
    summary_card = build_summary_card(
        {"dominant": ["earth"], "weak": ["metal"]},
        year_fortune,
        career,
        relationship,
        {"ten_gods": {"month": "상관"}},
        saju_result,
    )

    assert summary_card["year_trend"]
    assert summary_card["wealth"]
    assert " + " in summary_card["career"]
    assert " + " in summary_card["relationship"]
    assert summary_card["career"] != career["headline"].rstrip(".")
    assert summary_card["relationship"] != relationship["headline"].rstrip(".")


def test_summary_card_changes_with_different_charts():
    first_chart = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    first_daewoon = calculate_daewoon(first_chart, gender="male")
    first_year = calculate_yearly_fortune(first_chart, first_daewoon, 2026)
    first_summary = build_summary_card(
        {"dominant": ["earth"], "weak": ["metal"]},
        first_year,
        build_career_fortune(first_chart, first_year),
        build_relationship_fortune("male", first_year, first_chart),
        {"ten_gods": {"month": "상관"}},
        first_chart,
    )

    second_chart = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    second_daewoon = calculate_daewoon(second_chart, gender="female")
    second_year = calculate_yearly_fortune(second_chart, second_daewoon, 2026)
    second_summary = build_summary_card(
        {"dominant": ["earth", "water"], "weak": ["wood"]},
        second_year,
        build_career_fortune(second_chart, second_year),
        build_relationship_fortune("female", second_year, second_chart),
        {"ten_gods": {"month": "정관"}},
        second_chart,
    )

    assert first_summary["career"] != second_summary["career"]
    assert first_summary["relationship"] != second_summary["relationship"]


def test_summary_card_sentence_fragment_pool_is_significantly_expanded():
    total_fragments = 0
    sources = [
        summary_card_module.YEAR_PRIMARY_LINES,
        summary_card_module.YEAR_SECONDARY_LINES,
        summary_card_module.YEAR_MONTH_TEN_GOD_LINES,
        summary_card_module.WEALTH_BASE_LINES,
        summary_card_module.WEALTH_WEAK_LINES,
        summary_card_module.WEALTH_STAR_LINES,
        summary_card_module.WEALTH_DAY_STEM_LINES,
        summary_card_module.CAREER_BASE_BY_ELEMENT,
        summary_card_module.CAREER_MONTH_BRANCH_LINES,
        summary_card_module.CAREER_DAY_STEM_LINES,
        summary_card_module.CAREER_TREND_LINES,
        summary_card_module.CAREER_TONE_LINES,
        summary_card_module.CAREER_MONTH_STAR_LINES,
        summary_card_module.RELATION_BASE_BY_ELEMENT,
        summary_card_module.RELATION_TIME_BRANCH_LINES,
        summary_card_module.RELATION_DAY_STEM_LINES,
        summary_card_module.RELATION_TREND_LINES,
        summary_card_module.RELATION_INTENSITY_LINES,
        summary_card_module.RELATION_MONTH_STAR_LINES,
    ]

    for source in sources:
        total_fragments += sum(len(items) for items in source.values())

    assert total_fragments >= 350
