"""Tests for element analysis, ten gods, and interpretation."""

from data.day_pillar_sentences import DAY_PILLAR_SENTENCES
from data.month_ten_god_specialized import MONTH_TEN_GOD_CAREER_LINES, MONTH_TEN_GOD_RELATION_LINES
from services.analysis_sentence_store import load_analysis_sentences
from services.element_analyzer import analyze_elements
from services.interpretation import build_interpretation
from services.saju_calculator import get_basic_saju_result
from services.ten_gods import calculate_ten_gods

TRANSITIONS = ("그래서", "다만", "특히", "대신", "여기서 중요한 건", "결국")


def test_element_count_for_2006_case():
    saju = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)["saju"]
    analysis = analyze_elements(saju)

    assert analysis["elements"] == {
        "wood": 2,
        "fire": 2,
        "earth": 3,
        "metal": 0,
        "water": 1,
    }
    assert analysis["dominant"] == ["earth"]
    assert analysis["weak"] == ["metal"]


def test_ten_gods_for_2006_case():
    saju = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)["saju"]
    ten_gods = calculate_ten_gods(saju)

    assert ten_gods["ten_gods"] == {
        "year": "편재",
        "month": "상관",
        "time": "상관",
    }
    assert ten_gods["ten_gods_labels"] == {
        "year": "기회 포착",
        "month": "표현/변화",
        "time": "표현/변화",
    }
    assert ten_gods["ten_gods_details"] == {
        "year": "기회, 외부 확장",
        "month": "표현, 변화 압력",
        "time": "표현, 변화 압력",
    }
    assert "기회" in ten_gods["ten_gods_explanations"]["year"]
    assert "표현" in ten_gods["ten_gods_explanations"]["month"]


def test_ten_gods_for_1973_case():
    saju = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)["saju"]
    ten_gods = calculate_ten_gods(saju)

    assert ten_gods["ten_gods"] == {
        "year": "비견",
        "month": "정관",
        "time": "겁재",
    }


def test_interpretation_is_deterministic():
    saju = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)["saju"]
    analysis = analyze_elements(saju)

    first = build_interpretation(analysis)
    second = build_interpretation(analysis)

    assert first == second
    assert "토" in first["summary"]
    assert first["interpretation_sections"]["overall"]["one_line"]
    assert first["interpretation_sections"]["overall"]["highlight"]
    assert len(first["interpretation_sections"]["overall"]["easy_explanation"]) >= 2
    assert len(first["interpretation_sections"]["overall"]["real_life"]) >= 1
    assert len(first["interpretation_sections"]["overall"]["strength_and_risk"]) >= 2
    assert len(first["interpretation_sections"]["overall"]["action_advice"]) >= 1
    assert len(first["interpretation_sections"]["personality"]["real_life"]) >= 1
    assert len(first["interpretation_sections"]["personality"]["strength_and_risk"]) >= 2
    assert len(first["interpretation_sections"]["wealth"]["action_advice"]) >= 1
    combined_lines = (
        first["interpretation_sections"]["overall"]["easy_explanation"][1:]
        + first["interpretation_sections"]["overall"]["real_life"][1:]
        + first["interpretation_sections"]["overall"]["action_advice"][1:]
    )
    assert any(line.startswith(TRANSITIONS) for line in combined_lines)
    assert "맞습니다" not in first["interpretation_sections"]["overall"]["highlight"]


def test_element_tie_returns_multiple_dominant_and_weak():
    saju = {
        "year": {"stem": "병", "branch": "술"},
        "month": {"stem": "임", "branch": "자"},
        "day": {"stem": "무", "branch": "진"},
        "time": {"stem": "정", "branch": "해"},
    }
    analysis = analyze_elements(saju)

    assert analysis["elements"] == {
        "wood": 0,
        "fire": 2,
        "earth": 3,
        "metal": 0,
        "water": 3,
    }
    assert analysis["dominant"] == ["earth", "water"]
    assert analysis["weak"] == ["wood", "metal"]
    assert analysis["dominant_kor"] == ["토", "수"]
    assert analysis["weak_kor"] == ["목", "금"]


def test_interpretation_supports_multiple_dominant_elements():
    interpretation = build_interpretation(
        {
            "elements": {
                "wood": 0,
                "fire": 2,
                "earth": 2,
                "metal": 0,
                "water": 2,
            },
            "dominant": ["fire", "earth", "water"],
            "weak": ["wood", "metal"],
        }
    )

    assert "화, 토, 수" in interpretation["summary"]
    assert len(interpretation["interpretation_sections"]["overall"]["easy_explanation"]) >= 2
    assert len(interpretation["interpretation_sections"]["personality"]["real_life"]) >= 1
    assert len(interpretation["interpretation_sections"]["personality"]["strength_and_risk"]) >= 2
    assert len(interpretation["interpretation_sections"]["wealth"]["action_advice"]) >= 1


def test_support_message_strength_changes_with_count():
    medium_case = build_interpretation(
        {
            "elements": {
                "wood": 1,
                "fire": 2,
                "earth": 3,
                "metal": 1,
                "water": 1,
            },
            "dominant": ["earth"],
            "weak": ["wood", "metal", "water"],
        }
    )
    light_case = build_interpretation(
        {
            "elements": {
                "wood": 2,
                "fire": 3,
                "earth": 3,
                "metal": 2,
                "water": 2,
            },
            "dominant": ["fire", "earth"],
            "weak": ["wood", "metal", "water"],
        }
    )

    assert medium_case["interpretation_sections"]["personality"]["action_advice"]
    assert medium_case["interpretation_sections"]["wealth"]["action_advice"]
    assert light_case["interpretation_sections"]["personality"]["action_advice"]
    assert light_case["interpretation_sections"]["wealth"]["action_advice"]


def test_interpretation_sections_differ_between_requested_cases():
    first_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    second_result = get_basic_saju_result("solar", 2006, 8, 1, 13, 0)
    first_saju = first_result["saju"]
    second_saju = second_result["saju"]

    first = build_interpretation(analyze_elements(first_saju), saju_result=first_result)
    second = build_interpretation(analyze_elements(second_saju), saju_result=second_result)

    assert first["interpretation_sections"]["overall"]["one_line"] != second["interpretation_sections"]["overall"]["one_line"]
    assert first["interpretation_sections"]["personality"]["real_life"] != second["interpretation_sections"]["personality"]["real_life"]
    assert first["interpretation_sections"]["personality"]["strength_and_risk"] != second["interpretation_sections"]["personality"]["strength_and_risk"]
    assert first["interpretation_sections"]["wealth"]["action_advice"] != second["interpretation_sections"]["wealth"]["action_advice"]


def test_interpretation_includes_longform_pillar_sections():
    saju_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    analysis = analyze_elements(saju_result["saju"])
    ten_gods = calculate_ten_gods(saju_result["saju"])

    interpretation = build_interpretation(
        analysis,
        ten_gods=ten_gods,
        saju_result=saju_result,
    )

    pillar_sections = interpretation["interpretation_sections"]["pillars"]
    assert pillar_sections["year"]["title"] == "년주 해석"
    assert pillar_sections["month"]["title"] == "월주 해석"
    assert pillar_sections["day"]["title"] == "일주 해석"
    assert pillar_sections["time"]["title"] == "시주 해석"
    assert len(pillar_sections["year"]["easy_explanation"]) == 5
    assert len(pillar_sections["year"]["real_life"]) == 5
    assert len(pillar_sections["year"]["strength_and_risk"]) == 3
    assert len(pillar_sections["year"]["action_advice"]) == 2


def test_pillar_sections_differ_between_charts():
    first_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    second_result = get_basic_saju_result("solar", 1988, 5, 19, 18, 0)

    first = build_interpretation(
        analyze_elements(first_result["saju"]),
        ten_gods=calculate_ten_gods(first_result["saju"]),
        saju_result=first_result,
    )
    second = build_interpretation(
        analyze_elements(second_result["saju"]),
        ten_gods=calculate_ten_gods(second_result["saju"]),
        saju_result=second_result,
    )

    assert first["interpretation_sections"]["pillars"]["day"]["one_line"] != second["interpretation_sections"]["pillars"]["day"]["one_line"]
    assert first["interpretation_sections"]["pillars"]["month"]["real_life"] != second["interpretation_sections"]["pillars"]["month"]["real_life"]


def test_interpretation_uses_four_pillars_before_element_summary():
    result = get_basic_saju_result("solar", 2006, 8, 1, 13, 0)
    interpretation = build_interpretation(
        analyze_elements(result["saju"]),
        saju_result=result,
    )

    overall_text = " ".join(interpretation["interpretation_sections"]["overall"]["easy_explanation"])
    personality_text = " ".join(interpretation["interpretation_sections"]["personality"]["real_life"])
    wealth_text = " ".join(interpretation["interpretation_sections"]["wealth"]["easy_explanation"])

    assert "일간이" in overall_text
    assert "월지가" in overall_text
    assert "년주가" in overall_text
    assert "시지" in personality_text
    assert "일주" in wealth_text or "월주" in wealth_text


def test_analysis_sentence_json_has_required_branch_sets():
    data = load_analysis_sentences()

    assert len(data["day_stem"]) == 10
    assert len(data["month_branch"]) == 12
    assert len(data["year_stem"]) == 10
    assert len(data["time_branch"]) == 12
    assert len(data["month_ten_god"]) == 10
    assert len(data["daewoon_ten_god"]) == 10
    assert len(data["day_stem"]["갑"]["social_reaction"]) >= 3
    assert len(data["month_branch"]["자"]["money_habit"]) >= 3
    assert len(data["time_branch"]["해"]["intimate_reaction"]) >= 3


def test_day_pillar_and_month_ten_god_specialized_pools_exist():
    assert len(DAY_PILLAR_SENTENCES) == 60
    assert set(DAY_PILLAR_SENTENCES["갑자"]) == {"core", "career", "relationship", "wealth", "daily"}
    assert len(MONTH_TEN_GOD_CAREER_LINES) == 10
    assert len(MONTH_TEN_GOD_RELATION_LINES) == 10
    assert len(MONTH_TEN_GOD_CAREER_LINES["정관"]) >= 3
    assert len(MONTH_TEN_GOD_RELATION_LINES["편재"]) >= 3


def test_interpretation_uses_month_ten_god_and_daewoon_modifiers():
    result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    analysis = analyze_elements(result["saju"])
    ten_gods = calculate_ten_gods(result["saju"])
    from services.daewoon import calculate_daewoon

    daewoon = calculate_daewoon(result, gender="female")
    interpretation = build_interpretation(
        analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        saju_result=result,
    )

    overall_easy = " ".join(interpretation["interpretation_sections"]["overall"]["easy_explanation"])
    overall_action = " ".join(interpretation["interpretation_sections"]["overall"]["action_advice"])
    personality_easy = " ".join(interpretation["interpretation_sections"]["personality"]["easy_explanation"])
    wealth_easy = " ".join(interpretation["interpretation_sections"]["wealth"]["easy_explanation"])

    assert "월간 십성이" in personality_easy or "성격 보정으로 보면" in personality_easy or "월간에 " in personality_easy
    assert "재물 보정으로 보면" in wealth_easy or "월간 십성이" in wealth_easy
    assert "현재 대운" in overall_action or "이 시기" in overall_action or "지금은" in overall_action


def test_interpretation_includes_day_pillar_specific_sentence_layer():
    result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    interpretation = build_interpretation(
        analyze_elements(result["saju"]),
        ten_gods=calculate_ten_gods(result["saju"]),
        saju_result=result,
    )

    overall_easy = " ".join(interpretation["interpretation_sections"]["overall"]["easy_explanation"])
    personality_real = " ".join(interpretation["interpretation_sections"]["personality"]["real_life"])
    wealth_easy = " ".join(interpretation["interpretation_sections"]["wealth"]["easy_explanation"])

    assert result["saju"]["day"]["kor"] in overall_easy
    assert result["saju"]["day"]["kor"] in personality_real
    assert result["saju"]["day"]["kor"] in wealth_easy


def test_wealth_section_line_volume_is_expanded():
    result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    analysis = analyze_elements(result["saju"])
    ten_gods = calculate_ten_gods(result["saju"])
    from services.daewoon import calculate_daewoon
    from services.yearly_fortune import calculate_yearly_fortune

    daewoon = calculate_daewoon(result, gender="male")
    year_fortune = calculate_yearly_fortune(result, daewoon, 2026)
    interpretation = build_interpretation(
        analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        saju_result=result,
    )

    wealth = interpretation["interpretation_sections"]["wealth"]
    assert len(wealth["easy_explanation"]) >= 7
    assert len(wealth["real_life"]) >= 7
    assert len(wealth["strength_and_risk"]) >= 5
    assert len(wealth["action_advice"]) >= 3
