"""Tests for element analysis, ten gods, and interpretation."""

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
    first_saju = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)["saju"]
    second_saju = get_basic_saju_result("solar", 2006, 8, 1, 13, 0)["saju"]

    first = build_interpretation(analyze_elements(first_saju))
    second = build_interpretation(analyze_elements(second_saju))

    assert first["interpretation_sections"]["overall"]["one_line"] != second["interpretation_sections"]["overall"]["one_line"]
    assert first["interpretation_sections"]["personality"]["real_life"] != second["interpretation_sections"]["personality"]["real_life"]
    assert first["interpretation_sections"]["personality"]["strength_and_risk"] != second["interpretation_sections"]["personality"]["strength_and_risk"]
    assert first["interpretation_sections"]["wealth"]["action_advice"] != second["interpretation_sections"]["wealth"]["action_advice"]
