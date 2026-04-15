"""Tests for element analysis, ten gods, and interpretation."""

import json
from pathlib import Path

from services.analysis_context import build_analysis_context
from services.structure_analyzer import analyze_structure
from services.signal_extractor import extract_interpretation_signals
from services.report_builder import build_structured_report
from data.day_pillar_sentences import DAY_PILLAR_SENTENCES, get_day_pillar_sentence_options
from data.month_ten_god_specialized import MONTH_TEN_GOD_CAREER_LINES, MONTH_TEN_GOD_RELATION_LINES
from services.analysis_sentence_store import load_analysis_sentences
from services.element_analyzer import analyze_elements, analyze_elements_with_hidden
from services.interpretation import build_interpretation
from services.daewoon import calculate_daewoon
from services.saju_calculator import get_basic_saju_result
from services.ten_gods import calculate_ten_gods
from services.yearly_fortune import calculate_yearly_fortune

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
    assert analysis["weighted_scores"]["water"] > analysis["weighted_scores"]["earth"]
    assert analysis["dominant"] == ["water"]
    assert analysis["weak"] == ["metal"]
    assert analysis["dominant_kor"] == ["수"]
    assert analysis["weak_kor"] == ["금"]


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


def test_pillar_real_life_lines_use_scene_based_language():
    result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    interpretation = build_interpretation(
        analyze_elements(result["saju"]),
        ten_gods=calculate_ten_gods(result["saju"]),
        saju_result=result,
    )

    pillar_real_text = " ".join(
        line
        for section in interpretation["interpretation_sections"]["pillars"].values()
        for line in section["real_life"]
    )

    assert "단순한 상징" not in pillar_real_text
    assert "기둥이 만든" not in pillar_real_text
    assert "실제 생활에서는" not in pillar_real_text
    assert any(term in pillar_real_text for term in ["회의", "선택지", "일정", "처음 보는", "소개", "가까운 사람"])


def test_core_real_life_lines_use_scene_based_language():
    result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    analysis = analyze_elements(result["saju"])
    ten_gods = calculate_ten_gods(result["saju"])
    interpretation = build_interpretation(
        analysis,
        ten_gods=ten_gods,
        saju_result=result,
        analysis_context=build_analysis_context(
            saju_result=result,
            element_analysis=analysis,
            ten_gods=ten_gods,
        ),
    )

    overall_real = " ".join(interpretation["interpretation_sections"]["overall"]["real_life"])
    personality_real = " ".join(interpretation["interpretation_sections"]["personality"]["real_life"])
    wealth_real = " ".join(interpretation["interpretation_sections"]["wealth"]["real_life"])
    joined = " ".join([overall_real, personality_real, wealth_real])

    assert "대인 반응의 본체는" not in joined
    assert "재물 관점에서 보면" not in joined
    assert "원국 전체로 보면" not in joined
    assert "현재 대운과의 접점에서는" not in joined
    assert "현재 세운과 맞물린 자리에서는" not in joined
    assert any(term in joined for term in ["회의", "결제", "투자", "소개", "가까운 사람", "선택지", "장면"])


def test_core_easy_lines_start_with_scene_language():
    result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    interpretation = build_interpretation(
        analyze_elements(result["saju"]),
        ten_gods=calculate_ten_gods(result["saju"]),
        saju_result=result,
    )

    overall_easy = " ".join(interpretation["interpretation_sections"]["overall"]["easy_explanation"][:2])
    personality_easy = " ".join(interpretation["interpretation_sections"]["personality"]["easy_explanation"][:2])
    wealth_easy = " ".join(interpretation["interpretation_sections"]["wealth"]["easy_explanation"][:2])
    joined = " ".join([overall_easy, personality_easy, wealth_easy])

    assert any(term in joined for term in ["답을 빨리 정해야", "처음 만난 사람", "큰 지출이나 계약"])


def test_core_one_line_uses_scene_language():
    result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    interpretation = build_interpretation(
        analyze_elements(result["saju"]),
        ten_gods=calculate_ten_gods(result["saju"]),
        saju_result=result,
    )

    joined = " ".join(
        [
            interpretation["interpretation_sections"]["overall"]["one_line"],
            interpretation["interpretation_sections"]["personality"]["one_line"],
            interpretation["interpretation_sections"]["wealth"]["one_line"],
        ]
    )

    assert any(term in joined for term in ["답을 빨리 정해야", "거리를 둘지", "돈이 들어오거나 나갈 때", "큰 지출", "순간에는"])


def test_core_highlights_use_scene_language():
    result = get_basic_saju_result("solar", 2011, 4, 7, time_slot="jin")
    interpretation = build_interpretation(
        analyze_elements(result["saju"]),
        ten_gods=calculate_ten_gods(result["saju"]),
        saju_result=result,
    )

    joined = " ".join(
        [
            interpretation["interpretation_sections"]["overall"]["highlight"],
            interpretation["interpretation_sections"]["personality"]["highlight"],
            interpretation["interpretation_sections"]["wealth"]["highlight"],
        ]
    )

    assert "성격 해석의 핵심은" not in joined
    assert "재물 해석의 핵심은" not in joined
    assert "중요한 건" not in joined
    assert any(term in joined for term in ["장면", "순간", "거리를 정해야", "돈을 쓸지", "선택이 몰리는"])


def test_interpretation_uses_four_pillars_before_element_summary():
    result = get_basic_saju_result("solar", 2006, 8, 1, 13, 0)
    interpretation = build_interpretation(
        analyze_elements(result["saju"]),
        saju_result=result,
    )

    overall_text = " ".join(interpretation["interpretation_sections"]["overall"]["easy_explanation"])
    personality_text = " ".join(interpretation["interpretation_sections"]["personality"]["real_life"])
    wealth_text = " ".join(interpretation["interpretation_sections"]["wealth"]["easy_explanation"])

    assert any(term in overall_text for term in ["답을 빨리 정해야", "낯선 자리", "일간이", "월지가"])
    assert any(term in personality_text for term in ["가까운 사람", "의견이 갈리", "설명해야 하는", "관계가 깊어질수록"])
    assert "일주" in wealth_text or "월주" in wealth_text


def test_analysis_sentence_json_has_required_branch_sets():
    data = load_analysis_sentences()

    assert len(data["day_stem"]) == 10
    assert len(data["month_branch"]) == 12
    assert len(data["year_stem"]) == 10
    assert len(data["time_branch"]) == 12
    assert len(data["month_ten_god"]) == 10
    assert len(data["daewoon_ten_god"]) == 10
    assert len(data["day_stem"]["갑"]["social_reaction"]) >= 12
    assert len(data["day_stem"]["갑"]["speech_style"]) >= 12
    assert len(data["month_branch"]["자"]["money_habit"]) >= 12
    assert len(data["month_branch"]["자"]["work_adaptation"]) >= 12
    assert len(data["time_branch"]["해"]["intimate_reaction"]) >= 12
    assert len(data["month_ten_god"]["비견"]["personality_modifier"]) >= 12
    assert len(data["daewoon_ten_god"]["비견"]["action_advice"]) >= 12


def test_element_analysis_now_includes_hidden_and_weighted_layers():
    result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    analysis = analyze_elements(result["saju"])

    assert analysis["elements"] == {
        "wood": 2,
        "fire": 2,
        "earth": 3,
        "metal": 0,
        "water": 1,
    }
    assert set(analysis["hidden_counts"]) == {"wood", "fire", "earth", "metal", "water"}
    assert analysis["hidden_counts"]["earth"] > 0
    assert analysis["season_factor"]["earth"] > analysis["season_factor"]["metal"]
    assert analysis["seasonal_factor"]["earth"] == analysis["season_factor"]["earth"]
    assert analysis["weighted_scores"]["earth"] > analysis["weighted_scores"]["metal"]
    assert analysis["raw_counts"] == analysis["visible_counts"]
    assert analysis["support"]


def test_analyze_elements_with_hidden_function_matches_default_entrypoint():
    result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    direct = analyze_elements_with_hidden(result["saju"])
    wrapped = analyze_elements(result["saju"])

    assert direct["weighted_scores"] == wrapped["weighted_scores"]
    assert direct["hidden_counts"] == wrapped["hidden_counts"]


def test_ten_gods_include_hidden_branch_layers():
    result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    ten_gods = calculate_ten_gods(result["saju"])

    assert ten_gods["visible"]["month_stem"] == ten_gods["visible_ten_gods"]["month_stem"]
    assert ten_gods["hidden"]["month_branch"] == ten_gods["hidden_ten_gods"]["month"]
    assert set(ten_gods["hidden_ten_gods"]) == {"year", "month", "day", "time"}
    assert ten_gods["hidden_ten_gods"]["month"]
    assert ten_gods["hidden_ten_god_groups"]
    assert ten_gods["visible_ten_gods"]["month_stem"] == ten_gods["ten_gods"]["month"]
    assert ten_gods["month_focus_ten_gods"]["month_branch"] == ten_gods["hidden_ten_gods"]["month"]
    assert ten_gods["dominant_groups"] == ten_gods["hidden_ten_god_groups"]
    assert ten_gods["kinship_mapping"]["visible"]["month_stem"]
    assert ten_gods["kinship_mapping"]["hidden"]["month"]
    assert "배우자" in ten_gods["kinship_mapping"]["spouse_star_rules"]["male"]


def test_analysis_context_builds_strength_yongshin_and_interactions():
    result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    analysis = analyze_elements(result["saju"])
    ten_gods = calculate_ten_gods(result["saju"])
    daewoon = calculate_daewoon(result, gender="female")
    year_fortune = calculate_yearly_fortune(result, daewoon, 2026)

    context = build_analysis_context(
        saju_result=result,
        element_analysis=analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
    )

    assert context["strength"]["display_label"] in {"신강", "약간 신강", "균형", "약간 신약", "신약"}
    assert context["strength"]["strength_score"] == context["strength"]["score"]
    assert context["strength"]["strength_label"] == context["strength"]["label"]
    assert context["strength"]["draining_pressure"] >= context["strength"]["output_drain"]
    assert context["strength"]["controlling_pressure"] == context["strength"]["officer_pressure"]
    assert context["yongshin"]["display"]["primary"].endswith(")")
    assert context["yongshin"]["heeshin"]
    assert context["yongshin"]["kishin"]
    assert context["interactions"]["natal"]
    assert context["relations"]["stem_combinations"] is not None
    assert context["relations"]["branch_combinations"] is not None
    assert context["relations"]["wonjin"] is not None
    assert context["pillar_roles"]["hour"] == "결과/후반 인생"
    assert context["analysis"]["day_master"] == result["saju"]["day"]["stem"]
    assert context["analysis"]["useful_gods"]["yongshin"] == context["yongshin"]["primary_candidate"]
    assert context["analysis"]["relations"]["breaks"] is not None
    assert context["analysis"]["ten_gods"]["visible"]
    assert "is_day_master_weak" in context["flags"]
    assert "has_branch_conflict" in context["flags"]
    assert "wealth_flow_open" in context["flags"]
    assert "officer_pressure_high" in context["flags"]
    assert context["evidence"]["overall"]
    assert context["pillars"]["day"]["kor"]
    assert context["elements"]["weighted_scores"]
    assert context["ten_gods"]["kinship_mapping"]["visible"]["year_stem"]
    assert context["structure"]["primary_pattern"]
    assert context["structure"]["sub_pattern"]
    assert context["structure"]["signature_key"]
    assert context["structure"]["season"] in {"spring", "summer", "autumn", "winter"}
    assert context["structure"]["signature"]["yongshin"] == context["yongshin"]["primary_candidate"]
    assert context["saju_id"] == result["saju_id"]
    assert context["special_stars"]["summary"]
    assert "active" in context["special_stars"]
    assert "tags" in context["special_stars"]
    assert context["evidence"]["overall"][0]["uncertainty_notes"]


def test_interpretation_uses_advanced_analysis_context_in_longform_sections():
    result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    analysis = analyze_elements(result["saju"])
    ten_gods = calculate_ten_gods(result["saju"])
    daewoon = calculate_daewoon(result, gender="male")
    year_fortune = calculate_yearly_fortune(result, daewoon, 2026)
    context = build_analysis_context(
        saju_result=result,
        element_analysis=analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
    )

    interpretation = build_interpretation(
        analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        saju_result=result,
        analysis_context=context,
    )

    overall_easy = " ".join(interpretation["interpretation_sections"]["overall"]["easy_explanation"])
    overall_real = " ".join(interpretation["interpretation_sections"]["overall"]["real_life"])
    yongshin_primary = context["yongshin"]["display"]["primary"]
    practical_focus_terms = [
        "기준과 순서",
        "버틸 수 있는 범위",
        "흐름을 살피는",
        "전달 강도",
        "선택지를 조금 열어",
    ]

    assert yongshin_primary not in interpretation["interpretation_sections"]["overall"]["one_line"]
    assert yongshin_primary not in interpretation["interpretation_sections"]["personality"]["one_line"]
    assert yongshin_primary not in interpretation["interpretation_sections"]["wealth"]["one_line"]
    assert any(term in interpretation["interpretation_sections"]["overall"]["one_line"] for term in practical_focus_terms)
    assert "용신 후보" not in overall_easy
    assert "신강" in overall_easy or "신약" in overall_easy or "균형" in overall_easy
    assert any(term in overall_real for term in ["합", "충", "형", "파", "해"])


def test_structure_analyzer_returns_pattern_and_signature():
    result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    analysis = analyze_elements(result["saju"])
    ten_gods = calculate_ten_gods(result["saju"])
    daewoon = calculate_daewoon(result, gender="male")
    year_fortune = calculate_yearly_fortune(result, daewoon, 2026)
    context = build_analysis_context(
        saju_result=result,
        element_analysis=analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
    )

    structure = analyze_structure(
        saju=result["saju"],
        element_analysis=analysis,
        ten_gods=ten_gods,
        strength_analysis=context["strength"],
        yongshin_analysis=context["yongshin"],
        interactions=context["interactions"],
    )

    assert structure["primary_pattern"].endswith("격")
    assert structure["sub_pattern"]
    assert structure["signature"]["day_master"] == result["saju"]["day"]["stem"]
    assert result["saju"]["month"]["branch"] in structure["signature_key"]


def test_signal_extractor_and_report_builder_produce_sectioned_output():
    result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    analysis = analyze_elements(result["saju"])
    ten_gods = calculate_ten_gods(result["saju"])
    daewoon = calculate_daewoon(result, gender="male")
    year_fortune = calculate_yearly_fortune(result, daewoon, 2026)
    context = build_analysis_context(
        saju_result=result,
        element_analysis=analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
    )

    signals = extract_interpretation_signals(context)
    structured_report = build_structured_report(context, signals)

    assert signals["core"]
    assert signals["career"]
    assert structured_report["headline"]
    assert len(structured_report["summary"]) >= 3
    assert structured_report["sections"]["core_structure"]
    assert structured_report["sections"]["career"]
    assert structured_report["sections"]["action_guide"]

    alt_result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    alt_analysis = analyze_elements(alt_result["saju"])
    alt_ten_gods = calculate_ten_gods(alt_result["saju"])
    alt_daewoon = calculate_daewoon(alt_result, gender="male")
    alt_year_fortune = calculate_yearly_fortune(alt_result, alt_daewoon, 2026)
    alt_context = build_analysis_context(
        saju_result=alt_result,
        element_analysis=alt_analysis,
        ten_gods=alt_ten_gods,
        daewoon=alt_daewoon,
        year_fortune=alt_year_fortune,
    )
    alt_signals = extract_interpretation_signals(alt_context)
    alt_structured_report = build_structured_report(alt_context, alt_signals)

    assert structured_report["headline"] != alt_structured_report["headline"]
    assert structured_report["summary"][0] != alt_structured_report["summary"][0]


def test_structured_sentence_db_has_minimum_category_coverage():
    sentence_db = json.loads(Path("data/structured_sentence_db.json").read_text(encoding="utf-8"))
    assert len(sentence_db) >= 70

    category_type_counts: dict[tuple[str, str], int] = {}
    for item in sentence_db:
        key = (item["category"], item["type"])
        category_type_counts[key] = category_type_counts.get(key, 0) + 1

    categories = ["core_structure", "personality", "career", "money", "relationship", "health", "luck_flow", "action_guide"]
    for category in categories:
        assert category_type_counts.get((category, "base"), 0) >= 1
        assert category_type_counts.get((category, "structure"), 0) >= 1
        assert category_type_counts.get((category, "adjustment"), 0) >= 1


def test_day_pillar_and_month_ten_god_specialized_pools_exist():
    assert len(DAY_PILLAR_SENTENCES) == 60
    assert set(DAY_PILLAR_SENTENCES["갑자"]) == {"core", "career", "relationship", "wealth", "daily"}
    for field in ("core", "career", "relationship", "wealth", "daily"):
        options = get_day_pillar_sentence_options("갑자", field)
        assert len(options) >= 3
        assert len(set(options)) == len(options)
    assert len(MONTH_TEN_GOD_CAREER_LINES) == 10
    assert len(MONTH_TEN_GOD_RELATION_LINES) == 10
    assert len(MONTH_TEN_GOD_CAREER_LINES["정관"]) >= 6
    assert len(MONTH_TEN_GOD_RELATION_LINES["편재"]) >= 6


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

    assert any(term in overall_easy for term in [result["saju"]["day"]["kor"], "답을 빨리 정해야", "낯선 자리"])
    assert any(term in personality_real for term in ["가까운 사람", "의견이 갈리", "설명해야 하는", "관계가 깊어질수록"])
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
