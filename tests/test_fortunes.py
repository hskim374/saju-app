"""Tests for daewoon and fortune-layer services."""

from datetime import date

from data.month_ten_god_specialized import MONTH_TEN_GOD_CAREER_LINES, MONTH_TEN_GOD_RELATION_LINES
import services.summary_card as summary_card_module
from services.analysis_context import build_analysis_context
from services.career_fortune import build_career_fortune
import services.daily_fortune as daily_fortune_module
from services.daily_fortune import calculate_daily_fortune
from services.daewoon import calculate_daewoon
from services.element_analyzer import analyze_elements
from services.interpretation_engine import build_daily_section
import services.interpretation_templates as interpretation_templates_module
from services.monthly_fortune import calculate_monthly_fortune
from services.premium_report import build_premium_report
from services.relationship_fortune import build_relationship_fortune
from services.saju_calculator import get_basic_saju_result
from services.summary_card import build_summary_card
from services.ten_gods import calculate_ten_gods
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
    assert 9 <= first["score"]["value"] <= 99
    assert first["score"]["grade"]
    assert first["score"]["label"]
    assert first["score"]["summary"]
    assert first["score"]["driver_line"]
    assert first["score"]["guide_lines"]
    assert len(first["score"]["guide_lines"]) == len(daily_fortune_module.SCORE_GRADE_RULES)
    assert first["score"]["guide_lines"][0].startswith("90점 이상:")
    assert first["score"]["factor_highlights"]
    assert len(first["score"]["factor_highlights"]) <= 3
    assert first["score"]["reason_tag"]
    assert first["score"]["reason_tag"] in first["section"]["one_line"]
    assert first["score"]["grade"] in first["section"]["one_line"]
    expected_reason_line = daily_fortune_module.REASON_TAG_EXPLANATION[first["score"]["reason_tag"]]
    expected_action_pool = daily_fortune_module.REASON_TAG_ACTION_GUIDE[first["score"]["reason_tag"]]
    assert any(expected_reason_line in line for line in first["section"]["easy_explanation"])
    assert any(action_line in " ".join(first["section"]["action_advice"]) for action_line in expected_action_pool)
    assert "caution_tag" in first["score"]
    assert first["score"]["confidence"] in {"high", "medium", "low"}
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


def test_daily_score_label_and_summary_pools_are_expanded():
    label_total = sum(len(pool) for pool in daily_fortune_module.GRADE_LABEL_VARIANTS.values())
    summary_total = sum(len(pool) for pool in daily_fortune_module.REASON_TAG_SCORE_SUMMARY_VARIANTS.values())
    summary_total += sum(len(pool) for pool in daily_fortune_module.SCORE_BUCKET_SUMMARY_VARIANTS.values())

    assert label_total == 18
    assert summary_total == 36


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
    assert top_score["label"]
    assert low_score["label"]
    assert top_score["summary"]
    assert low_score["summary"]


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


def test_shared_interpretation_template_pools_are_significantly_expanded():
    assert len(interpretation_templates_module.PERSONALITY_SUMMARY) >= 20
    assert len(interpretation_templates_module.PERSONALITY_REAL_LIFE) >= 20
    assert len(interpretation_templates_module.PERSONALITY_ACTION) >= 20
    assert len(interpretation_templates_module.MONEY_SUMMARY) >= 20
    assert len(interpretation_templates_module.MONEY_REAL_LIFE) >= 20
    assert len(interpretation_templates_module.MONEY_ACTION) >= 20
    assert len(interpretation_templates_module.CAREER_SUMMARY) >= 20
    assert len(interpretation_templates_module.CAREER_REAL_LIFE) >= 20
    assert len(interpretation_templates_module.CAREER_ACTION) >= 20
    assert len(interpretation_templates_module.RELATIONSHIP_SUMMARY) >= 20
    assert len(interpretation_templates_module.RELATIONSHIP_REAL_LIFE) >= 20
    assert len(interpretation_templates_module.RELATIONSHIP_ACTION) >= 20
    assert len(interpretation_templates_module.FORTUNE_SUMMARY) >= 25
    assert len(interpretation_templates_module.FORTUNE_EXPLAIN) >= 25
    assert len(interpretation_templates_module.FORTUNE_REAL_LIFE) >= 20
    assert len(interpretation_templates_module.FORTUNE_ACTION) >= 25
    assert len(interpretation_templates_module.DAILY_SUMMARY) >= 20
    assert len(interpretation_templates_module.DAILY_EXPLAIN) >= 20
    assert len(interpretation_templates_module.DAILY_REAL_LIFE) >= 20
    assert len(interpretation_templates_module.DAILY_ACTION) >= 20


def test_daily_section_keeps_context_but_still_surfaces_shared_pool_lines():
    section = build_daily_section(
        headline="오늘은 정리와 완료에 강한 날입니다.",
        explanation="마감과 점검이 체감 차이를 만들 수 있습니다.",
        advice="할 일 두 개만 남기고 나머지는 보류하세요.",
        keywords=["정리", "마감", "실무"],
        seed=7,
        context_easy_lines=[f"context easy {index}" for index in range(5)],
        context_real_lines=[f"context real {index}" for index in range(6)],
        context_action_lines=[f"context action {index}" for index in range(3)],
    )

    assert any("context easy" not in line for line in section["easy_explanation"])
    assert any("context real" not in line for line in section["real_life"])
    assert any("context action" not in line for line in section["action_advice"])


def test_career_and_relationship_real_life_lines_use_scene_language():
    saju_result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    element_analysis = analyze_elements(saju_result["saju"])
    ten_gods = calculate_ten_gods(saju_result["saju"])
    daewoon = calculate_daewoon(saju_result, gender="male")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)
    analysis_context = build_analysis_context(
        saju_result=saju_result,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
    )

    career = build_career_fortune(saju_result, year_fortune, analysis_context=analysis_context)
    relationship = build_relationship_fortune(
        "male",
        year_fortune,
        saju_result=saju_result,
        analysis_context=analysis_context,
    )

    career_real = " ".join(career["section"]["real_life"])
    relationship_real = " ".join(relationship["section"]["real_life"])
    joined = " ".join([career_real, relationship_real])

    assert "를 직장 쪽으로 풀면" not in joined
    assert "를 관계 쪽으로 읽으면" not in joined
    assert "현재 대운과 원국은" not in joined
    assert "올해 세운과 원국은" not in joined
    assert "원국 안에는" not in joined
    assert any(term in joined for term in ["역할", "평가", "팀 변화", "연락", "관계 정의", "거리", "장면"])


def test_career_and_relationship_easy_lines_start_with_scene_language():
    saju_result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    daewoon = calculate_daewoon(saju_result, gender="male")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)

    career = build_career_fortune(saju_result, year_fortune)
    relationship = build_relationship_fortune("male", year_fortune, saju_result)

    joined = " ".join(career["section"]["easy_explanation"][:2] + relationship["section"]["easy_explanation"][:2])
    assert any(term in joined for term in ["팀 안에서", "연락을 이어 갈지", "직장에서는", "관계는"])


def test_daily_career_and_relationship_headlines_use_scene_language():
    saju_result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    daewoon = calculate_daewoon(saju_result, gender="male")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)
    daily = calculate_daily_fortune(saju_result, date(2026, 4, 10))
    career = build_career_fortune(saju_result, year_fortune)
    relationship = build_relationship_fortune("male", year_fortune, saju_result)

    joined = " ".join([daily["headline"], career["headline"], relationship["headline"]])
    assert any(term in joined for term in ["갑자기 결정을", "역할이 커지거나", "가까워질지 거리를 둘지", "장면에서는"])


def test_daily_career_and_relationship_highlights_use_scene_language():
    saju_result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    daewoon = calculate_daewoon(saju_result, gender="male")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)
    daily = calculate_daily_fortune(saju_result, date(2026, 4, 10))
    career = build_career_fortune(saju_result, year_fortune)
    relationship = build_relationship_fortune("male", year_fortune, saju_result)

    joined = " ".join([daily["section"]["highlight"], career["section"]["highlight"], relationship["section"]["highlight"]])
    assert "중요한 건" not in joined
    assert any(term in joined for term in ["장면", "순간", "연락", "역할", "결정을", "거리"])


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
    assert all(item["reason_tag"] for item in weekly)
    assert all("caution_tag" in item for item in weekly)
    assert all(item["confidence"] in {"high", "medium", "low"} for item in weekly)
    assert all(item["confidence_label"] in {"확신 높음", "확신 중간", "보수 해석"} for item in weekly)
    assert all(item["driver_line"] for item in weekly)
    assert all(item["factor_top"] for item in weekly)
    assert all(item["factor_top_compact"] for item in weekly)
    assert all(item["summary"] for item in weekly)
    assert all(len(item["summary"]) <= 20 for item in weekly)
    assert len({item["date"] for item in weekly}) == 7
    assert len({item["summary"] for item in weekly}) >= 5
    assert len({item["driver_line"] for item in weekly if item["driver_line"]}) >= 4


def test_weekly_short_summary_can_use_reason_tag_pool():
    summary = weekly_fortune_module._build_short_summary(
        {
            "score": {"value": 88, "reason_tag": "용신 정합"},
            "keywords": ["성과", "실행", "정리"],
        },
        date(2026, 4, 8),
    )

    assert summary in weekly_fortune_module.REASON_TAG_SHORT_POOLS["용신 정합"]


def test_weekly_short_summary_can_use_reason_caution_combo_pool():
    summary = weekly_fortune_module._build_short_summary(
        {
            "score": {"value": 84, "reason_tag": "실행 기회", "caution_tag": "충돌 주의", "confidence": "medium"},
            "keywords": ["성과", "실행", "정리"],
        },
        date(2026, 4, 8),
    )

    assert summary in weekly_fortune_module.REASON_CAUTION_SHORT_POOLS[("실행 기회", "충돌 주의")]


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
    assert any(term in first_real for term in ["회의", "답장", "결제", "장면"])


def test_daily_fortune_summary_and_front_lines_use_scene_language():
    saju_result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    daily = calculate_daily_fortune(saju_result, date(2026, 4, 10))

    joined = " ".join(
        [
            daily["summary"],
            daily["section"]["easy_explanation"][0],
            daily["section"]["real_life"][0],
        ]
    )

    assert "일주를 기준으로 보면" not in joined
    assert "원국 일주" not in joined
    assert "일주 기준의 오늘 반응을 보면" not in joined
    assert "성과과" not in joined
    assert "주의과" not in joined
    assert any(term in joined for term in ["장면", "순간", "회의", "답장", "결제", "답을 정"])


def test_daily_fortune_easy_explanation_avoids_internal_engine_terms():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    daily = calculate_daily_fortune(saju_result, date(2026, 4, 10))

    joined = " ".join(daily["section"]["easy_explanation"][:4])

    assert "신약" not in joined
    assert "보조로는" not in joined
    assert "금(金)" not in joined
    assert "수(水)" not in joined
    assert "정해(" not in joined
    assert "일간답게" not in joined
    assert "월지답게" not in joined
    assert "그래서," not in joined
    assert "결국 오늘은" not in joined
    assert any(term in joined for term in ["피로", "기준", "범위", "흐름", "선택", "결론"])


def test_daily_fortune_headline_is_compact_and_scene_based():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    daily = calculate_daily_fortune(saju_result, date(2026, 4, 10))

    headline = daily["headline"]

    assert headline.count(".") <= 1
    assert "오늘의 핵심은" not in headline
    assert any(term in headline for term in ["순간", "장면", "회의", "답장", "결제", "선택지"])


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

    assert daily["day_context"] == day_kor
    assert "일주 기준" not in daily["explanation"]
    assert "일주 기준" not in " ".join(daily["section"]["easy_explanation"])
    assert day_kor in career["headline"]
    assert day_kor in relationship["headline"]
    assert any(month_ten_god in line for line in career["section"]["easy_explanation"])
    assert any(month_ten_god in line for line in relationship["section"]["easy_explanation"])
    assert any(line in " ".join(career["section"]["easy_explanation"]) for line in MONTH_TEN_GOD_CAREER_LINES[month_ten_god])
    assert any(line in " ".join(relationship["section"]["easy_explanation"]) for line in MONTH_TEN_GOD_RELATION_LINES[month_ten_god])


def test_fortunes_can_surface_analysis_context_lines():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    element_analysis = analyze_elements(saju_result["saju"])
    ten_gods = calculate_ten_gods(saju_result["saju"])
    daewoon = calculate_daewoon(saju_result, gender="female")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)
    base_daily = calculate_daily_fortune(saju_result, date(2026, 3, 31))
    analysis_context = build_analysis_context(
        saju_result=saju_result,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        daily_fortune=base_daily,
    )

    daily = calculate_daily_fortune(saju_result, date(2026, 3, 31), analysis_context=analysis_context)
    career = build_career_fortune(saju_result, year_fortune, analysis_context=analysis_context)
    relationship = build_relationship_fortune("female", year_fortune, saju_result, analysis_context=analysis_context)

    assert any("먼저 끝낼 일 하나를 정하고" in line or "기준과 순서를 먼저 분명히 하고" in line for line in daily["section"]["easy_explanation"])
    assert any("버틸 범위와 마감 간격" in line or "기준과 순서를 먼저 분명히 하는" in line for line in career["section"]["easy_explanation"])
    assert any("템포를 늦추고 회복할 간격" in line or "관계 기준과 선을 먼저 분명히 하는" in line for line in relationship["section"]["easy_explanation"])
    assert not any("(金)" in line or "(水)" in line or "(木)" in line or "(火)" in line or "(土)" in line for line in career["section"]["easy_explanation"])
    assert not any("(金)" in line or "(水)" in line or "(木)" in line or "(火)" in line or "(土)" in line for line in relationship["section"]["easy_explanation"])
    assert not any("일주를 직장 쪽으로 보면" in line or "일하는 방식에서도" in line for line in career["section"]["easy_explanation"])
    assert not any("일주를 관계 쪽으로 읽으면" in line or "대인관계에서도" in line for line in relationship["section"]["easy_explanation"])
    assert not any("세운 " in line or "대운 " in line or "월지 " in line for line in career["section"]["action_advice"])
    assert not any("세운 " in line or "대운 " in line or "월지 " in line for line in relationship["section"]["action_advice"])
    assert any("일정, 사람, 돈 문제가" in line or "원래부터 같은 문제를" in line for line in daily["section"]["real_life"])
    assert any("역할이 바뀌거나 책임 범위가 넓어지는" in line or "평가, 이동, 팀 변화" in line for line in career["section"]["real_life"])
    assert any("좋아도 바로 다가갈지" in line or "연락 빈도와 관계 속도" in line for line in relationship["section"]["real_life"])


def test_daily_score_with_analysis_context_surfaces_reason_tag_and_confidence():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    element_analysis = analyze_elements(saju_result["saju"])
    ten_gods = calculate_ten_gods(saju_result["saju"])
    daewoon = calculate_daewoon(saju_result, gender="female")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)
    base_daily = calculate_daily_fortune(saju_result, date(2026, 3, 31))
    analysis_context = build_analysis_context(
        saju_result=saju_result,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        daily_fortune=base_daily,
    )

    daily = calculate_daily_fortune(saju_result, date(2026, 3, 31), analysis_context=analysis_context)

    assert daily["score"]["reason_tag"] in {
        "용신 정합",
        "균형 회복",
        "실행 기회",
        "재물 흐름",
        "관계 조율",
        "정리 우선",
        "속도 조절",
        "변동 관리",
        "변동 주의",
        "리듬 주의",
        "압력 주의",
        "방어 우선",
    }
    assert daily["score"]["caution_tag"] in {
        None,
        "변동 주의",
        "리듬 주의",
        "압력 주의",
        "충돌 주의",
        "방어 우선",
    }
    assert daily["score"]["confidence"] in {"high", "medium", "low"}
    factor_names = {factor["name"] for factor in daily["score"]["factors"]}
    assert factor_names & {"구조 정합", "구조 역행", "신살 보정", "관계 플래그", "시간 테마"}
    assert daily["score"]["reason_tag"] in daily["section"]["one_line"]
    assert any(text.startswith("상승:") or text.startswith("주의:") for text in daily["score"]["factor_highlights"])
    assert any(
        token in daily["score"]["summary"]
        for token in [
            "체감 성과",
            "조건표",
            "책임 범위",
            "핵심 정보",
            "협업과 단독",
            "사람이 모이는 자리",
            "변동이 많은 날",
            "집중 시간이 확보되면",
        ]
    )


def test_v2_score_distribution_expansion_keeps_center_and_widens_extremes():
    base = daily_fortune_module.DAILY_SCORE_V2_BASE

    assert daily_fortune_module._expand_v2_score_distribution(base) == base
    assert daily_fortune_module._expand_v2_score_distribution(base + 18) > base + 18
    assert daily_fortune_module._expand_v2_score_distribution(base - 18) < base - 18


def test_male_sample_month_distribution_reaches_wider_daily_score_range():
    saju_result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    saju_result["raw_input"]["gender"] = "male"
    element_analysis = analyze_elements(saju_result["saju"])
    ten_gods = calculate_ten_gods(saju_result["saju"])
    daewoon = calculate_daewoon(saju_result, gender="male")
    yearly_cache: dict[int, dict] = {}
    scores: list[int] = []

    for offset in range(30):
        target_date = date(2026, 4, 9).fromordinal(date(2026, 4, 9).toordinal() + offset)
        base_daily = calculate_daily_fortune(saju_result, target_date)
        year_fortune = yearly_cache.get(target_date.year)
        if year_fortune is None:
            year_fortune = calculate_yearly_fortune(saju_result, daewoon, target_date.year)
            yearly_cache[target_date.year] = year_fortune
        analysis_context = build_analysis_context(
            saju_result=saju_result,
            element_analysis=element_analysis,
            ten_gods=ten_gods,
            daewoon=daewoon,
            year_fortune=year_fortune,
            daily_fortune=base_daily,
        )
        daily = calculate_daily_fortune(saju_result, target_date, analysis_context=analysis_context)
        scores.append(daily["score"]["value"])

    assert max(scores) >= 99
    assert min(scores) <= 36


def test_high_score_sample_prefers_positive_reason_tag_over_warning_tag():
    saju_result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    saju_result["raw_input"]["gender"] = "male"
    element_analysis = analyze_elements(saju_result["saju"])
    ten_gods = calculate_ten_gods(saju_result["saju"])
    daewoon = calculate_daewoon(saju_result, gender="male")
    target_date = date(2026, 4, 26)
    base_daily = calculate_daily_fortune(saju_result, target_date)
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, target_date.year)
    analysis_context = build_analysis_context(
        saju_result=saju_result,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        daily_fortune=base_daily,
    )

    daily = calculate_daily_fortune(saju_result, target_date, analysis_context=analysis_context)

    assert daily["score"]["value"] >= 90
    assert daily["score"]["reason_tag"] in {
        "용신 정합",
        "균형 회복",
        "실행 기회",
        "재물 흐름",
        "관계 조율",
        "정리 우선",
    }
    assert daily["score"]["caution_tag"] in {
        None,
        "변동 주의",
        "리듬 주의",
        "압력 주의",
        "충돌 주의",
        "방어 우선",
    }


def test_yearly_monthly_and_premium_can_use_analysis_context():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    element_analysis = analyze_elements(saju_result["saju"])
    ten_gods = calculate_ten_gods(saju_result["saju"])
    daewoon = calculate_daewoon(saju_result, gender="female")
    base_year = calculate_yearly_fortune(saju_result, daewoon, 2026)
    base_daily = calculate_daily_fortune(saju_result, date(2026, 3, 31))
    analysis_context = build_analysis_context(
        saju_result=saju_result,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=base_year,
        daily_fortune=base_daily,
    )
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026, analysis_context=analysis_context)
    monthly = calculate_monthly_fortune(saju_result, 2026, analysis_context=analysis_context)
    career = build_career_fortune(saju_result, year_fortune, analysis_context=analysis_context)
    relationship = build_relationship_fortune("female", year_fortune, saju_result, analysis_context=analysis_context)
    premium = build_premium_report(
        saju_result=saju_result,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        career_fortune=career,
        relationship_fortune=relationship,
        interpretation={"interpretation_sections": {"overall": {"highlight": "기준을 먼저 세우는 힘이 남아 있습니다."}}},
        premium_enabled=True,
        analysis_context=analysis_context,
    )

    assert "중간 계산상" in year_fortune["summary"] or "중간 계산상" in year_fortune["explanation"]
    assert not any(term in monthly[0]["summary"] for term in ["목(木)", "화(火)", "토(土)", "금(金)", "수(水)", "중간 계산상"])
    assert not any(term in monthly[0]["explanation"] for term in ["목 기운", "화 기운", "토 기운", "금 기운", "수 기운", "중간 계산상"])
    assert any(term in monthly[0]["summary"] for term in ["일정", "예산", "기준", "준비", "정리", "사람", "답"])
    assert premium["analysis_brief"]["brief"]
    assert any("용신 후보" in line or "핵심 용신 후보" in line for line in premium["analysis_brief"]["brief"] + premium["overview"])


def test_monthly_fortune_uses_scene_language_in_summary_explanation_and_advice():
    saju_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    element_analysis = analyze_elements(saju_result["saju"])
    ten_gods = calculate_ten_gods(saju_result["saju"])
    daewoon = calculate_daewoon(saju_result, gender="male")
    year_fortune = calculate_yearly_fortune(saju_result, daewoon, 2026)
    daily = calculate_daily_fortune(saju_result, date(2026, 4, 10))
    analysis_context = build_analysis_context(
        saju_result=saju_result,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        daily_fortune=daily,
    )

    monthly = calculate_monthly_fortune(saju_result, 2026, analysis_context=analysis_context)
    joined = " ".join([monthly[0]["headline"], monthly[0]["summary"], monthly[0]["explanation"], monthly[0]["advice"]])

    assert "중간 계산상" not in joined
    assert "목 기운" not in joined
    assert "화 기운" not in joined
    assert "토 기운" not in joined
    assert "금 기운" not in joined
    assert "수 기운" not in joined
    assert "금(金)" not in joined
    assert any(term in joined for term in ["일정", "예산", "기준", "정리", "준비", "사람", "답"])


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
