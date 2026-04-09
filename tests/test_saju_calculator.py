"""Tests for the real saju calculator."""

from services.saju_calculator import get_basic_saju_result


def test_solar_input_returns_expected_pillars_for_2006_case():
    result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)

    assert result["saju"]["year"]["kor"] == "병술"
    assert result["saju"]["month"]["kor"] == "을미"
    assert result["saju"]["day"]["kor"] == "임술"
    assert result["saju"]["time"]["kor"] == "을사"
    assert result["debug"]["day_pillar"]["all_methods_match"] is True


def test_solar_input_returns_expected_pillars_for_1973_case():
    result = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)

    assert result["saju"]["year"]["kor"] == "계축"
    assert result["saju"]["month"]["kor"] == "무오"
    assert result["saju"]["day"]["kor"] == "계유"
    assert result["saju"]["time"]["kor"] == "임술"
    assert result["debug"]["day_pillar"]["all_methods_match"] is True


def test_lunar_input_matches_same_solar_result():
    solar_result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    lunar_result = get_basic_saju_result("lunar", 2006, 7, 8, 10, 0)

    assert lunar_result["resolved_solar"]["iso"] == "2006-08-01"
    assert lunar_result["saju"] == solar_result["saju"]


def test_leap_month_input_is_supported():
    result = get_basic_saju_result("lunar", 2017, 5, 1, 13, 0, is_leap_month=True)

    assert result["resolved_solar"]["iso"] == "2017-06-24"
    assert result["saju"]["year"]["kor"] == "정유"
    assert result["saju"]["month"]["kor"] == "병오"
    assert result["saju"]["day"]["kor"] == "임오"
    assert result["saju"]["time"]["kor"] == "정미"


def test_same_input_is_deterministic():
    first = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)
    second = get_basic_saju_result("solar", 1973, 6, 6, 20, 30)

    assert first == second


def test_li_chun_boundary_uses_korea_timezone():
    result = get_basic_saju_result("solar", 2017, 2, 3, 23, 50)

    assert result["saju"]["year"]["kor"] == "병신"
    assert result["saju"]["month"]["kor"] == "신축"


def test_day_pillar_debug_contains_epoch_and_jdn():
    result = get_basic_saju_result("solar", 2006, 8, 1, 10, 0)
    debug = result["debug"]["day_pillar"]

    assert debug["epoch_date"] == "2000-01-07"
    assert debug["epoch_ganzhi"] == "갑자"
    assert debug["jdn"] == 2453949
    assert debug["epoch_offset_days"] == 2398


def test_time_slot_input_maps_to_saju_time_basis():
    result = get_basic_saju_result("solar", 2006, 8, 1, time_slot="mi")

    assert result["time_basis"]["input_label"] == "미시 (13:00~14:59)"
    assert result["time_basis"]["saju_time_kor"] == "미시"
    assert result["saju"]["time"]["branch"] == "미"
    assert "notes" in result["sensitivity"]


def test_saju_result_includes_sensitivity_hooks():
    result = get_basic_saju_result("solar", 2017, 2, 3, 23, 50)

    assert "sensitivity" in result
    assert "late_night_birth" in result["sensitivity"]
    assert "near_major_solar_term" in result["sensitivity"]
    assert result["sensitivity"]["previous_major_term"] or result["sensitivity"]["next_major_term"]


def test_both_ja_time_slots_calculate_as_ja_time():
    early = get_basic_saju_result("solar", 2006, 8, 1, time_slot="early_ja")
    late = get_basic_saju_result("solar", 2006, 8, 1, time_slot="late_ja")

    assert early["time_basis"]["saju_time_kor"] == "자시"
    assert late["time_basis"]["saju_time_kor"] == "자시"
    assert early["saju"]["time"]["kor"] == late["saju"]["time"]["kor"]
