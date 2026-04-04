"""Helpers for user-facing Hangul/Hanja pillar display."""

from __future__ import annotations

from copy import deepcopy
import re

from data.branches import BRANCHES, BRANCHES_BY_HANJA, BRANCHES_BY_KOR
from data.stems import STEMS, STEMS_BY_HANJA, STEMS_BY_KOR

GANZHI_CYCLE = [
    {
        "kor": f"{STEMS[index % 10]['kor']}{BRANCHES[index % 12]['kor']}",
        "hanja": f"{STEMS[index % 10]['hanja']}{BRANCHES[index % 12]['hanja']}",
    }
    for index in range(60)
]

PILLAR_LABEL_BY_KOR = {item["kor"]: f"{item['kor']}({item['hanja']})" for item in GANZHI_CYCLE}
PILLAR_LABEL_BY_HANJA = {item["hanja"]: f"{item['kor']}({item['hanja']})" for item in GANZHI_CYCLE}
STEM_LABEL_BY_KOR = {item["kor"]: f"{item['kor']}({item['hanja']})" for item in STEMS}
STEM_LABEL_BY_HANJA = {item["hanja"]: f"{item['kor']}({item['hanja']})" for item in STEMS}
BRANCH_LABEL_BY_KOR = {item["kor"]: f"{item['kor']}({item['hanja']})" for item in BRANCHES}
BRANCH_LABEL_BY_HANJA = {item["hanja"]: f"{item['kor']}({item['hanja']})" for item in BRANCHES}
YIN_YANG_LABELS = {"yang": "양(陽)", "yin": "음(陰)"}
ELEMENT_LABELS = {
    "wood": "목(木)",
    "fire": "화(火)",
    "earth": "토(土)",
    "metal": "금(金)",
    "water": "수(水)",
}

_PILLAR_KOR_PATTERN = re.compile("|".join(re.escape(value) for value in PILLAR_LABEL_BY_KOR))
_PILLAR_HANJA_PATTERN = re.compile("|".join(re.escape(value) for value in PILLAR_LABEL_BY_HANJA))
_STEM_PATTERN = "[갑을병정무기경신임계甲乙丙丁戊己庚辛壬癸]"
_BRANCH_PATTERN = "[자축인묘진사오미신유술해子丑寅卯辰巳午未申酉戌亥]"
_STEM_BEFORE_PATTERN = re.compile(rf"({_STEM_PATTERN})(?![\(（])(?=\s*(?:일간|천간))")
_STEM_AFTER_PATTERN = re.compile(rf"(?<=(?:일간|천간|년간|월간|시간)\s)({_STEM_PATTERN})(?![\(（])")
_BRANCH_BEFORE_PATTERN = re.compile(rf"({_BRANCH_PATTERN})(?![\(（])(?=\s*지지)")
_BRANCH_AFTER_PATTERN = re.compile(rf"(?<=(?:지지|년지|월지|일지|시지)\s)({_BRANCH_PATTERN})(?![\(（])")
_SKIP_STRING_KEYS = {
    "kor",
    "hanja",
    "stem",
    "branch",
    "stem_hanja",
    "branch_hanja",
}


def build_display_result(result_data: dict) -> dict:
    """Return a user-facing copy with Hangul/Hanja labels normalized."""
    display = deepcopy(result_data)
    _attach_display_fields(display)
    return _localize_value(display)


def format_pillar_label(kor: str, hanja: str | None = None) -> str:
    """Return a Korean/Hanja display string such as 경자(庚子)."""
    if not kor:
        return kor
    resolved_hanja = hanja or PILLAR_LABEL_BY_KOR.get(kor, "")
    if resolved_hanja and "(" in resolved_hanja:
        return resolved_hanja
    if not hanja and kor in PILLAR_LABEL_BY_KOR:
        return PILLAR_LABEL_BY_KOR[kor]
    if hanja:
        return f"{kor}({hanja})"
    return kor


def format_stem_label(value: str) -> str:
    if value in STEM_LABEL_BY_KOR:
        return STEM_LABEL_BY_KOR[value]
    if value in STEM_LABEL_BY_HANJA:
        return STEM_LABEL_BY_HANJA[value]
    return value


def format_branch_label(value: str) -> str:
    if value in BRANCH_LABEL_BY_KOR:
        return BRANCH_LABEL_BY_KOR[value]
    if value in BRANCH_LABEL_BY_HANJA:
        return BRANCH_LABEL_BY_HANJA[value]
    return value


def format_yin_yang_label(value: str) -> str:
    return YIN_YANG_LABELS.get(value, value)


def format_element_label(value: str) -> str:
    return ELEMENT_LABELS.get(value, value)


def localize_text(text: str) -> str:
    """Normalize visible text to Hangul(Hanja) and remove stray English labels."""
    text = text.replace("실행 전략 (Action Plan)", "실행 전략")
    text = _replace_unformatted_pillars(text)
    text = _replace_stem_terms(text)
    text = _replace_branch_terms(text)
    return text


def _attach_display_fields(display: dict) -> None:
    saju = display.get("saju", {})
    for pillar in saju.values():
        if pillar is None:
            continue
        pillar["display"] = format_pillar_label(pillar["kor"], pillar.get("hanja"))
        pillar["stem_display"] = format_stem_label(pillar["stem"])
        pillar["branch_display"] = format_branch_label(pillar["branch"])

    daewoon = display.get("daewoon")
    if daewoon:
        for cycle in daewoon.get("cycles", []):
            cycle["pillar_display"] = format_pillar_label(cycle["pillar"], cycle.get("hanja"))
        active_cycle_summary = daewoon.get("active_cycle_summary")
        if active_cycle_summary:
            active_cycle_summary["pillar_display"] = format_pillar_label(active_cycle_summary["pillar"])

    year_fortune = display.get("year_fortune")
    if year_fortune:
        year_fortune["pillar_display"] = format_pillar_label(year_fortune["pillar"], year_fortune.get("hanja"))
        if year_fortune.get("active_daewoon"):
            year_fortune["active_daewoon"]["pillar_display"] = format_pillar_label(
                year_fortune["active_daewoon"]["pillar"]
            )

    daily_fortune = display.get("daily_fortune")
    if daily_fortune:
        daily_fortune["pillar_display"] = format_pillar_label(daily_fortune["pillar"], daily_fortune.get("hanja"))

    for item in display.get("monthly_fortune", []):
        item["pillar_display"] = format_pillar_label(item["pillar"], item.get("hanja"))

    selected_month_fortune = display.get("selected_month_fortune")
    if selected_month_fortune:
        selected_month_fortune["pillar_display"] = format_pillar_label(
            selected_month_fortune["pillar"],
            selected_month_fortune.get("hanja"),
        )


def _localize_value(value, key: str | None = None):
    if isinstance(value, dict):
        return {dict_key: _localize_value(dict_value, dict_key) for dict_key, dict_value in value.items()}
    if isinstance(value, list):
        return [_localize_value(item, key) for item in value]
    if isinstance(value, str):
        if key in _SKIP_STRING_KEYS:
            return value
        return localize_text(value)
    return value


def _replace_unformatted_pillars(text: str) -> str:
    def replace_kor(match: re.Match[str]) -> str:
        start, end = match.span()
        if end < len(text) and text[end] in "(（":
            return match.group(0)
        return PILLAR_LABEL_BY_KOR[match.group(0)]

    def replace_hanja(match: re.Match[str]) -> str:
        start, end = match.span()
        if start > 0 and text[start - 1] in "(（" and end < len(text) and text[end] in ")）":
            return match.group(0)
        return PILLAR_LABEL_BY_HANJA[match.group(0)]

    text = _PILLAR_KOR_PATTERN.sub(replace_kor, text)
    return _PILLAR_HANJA_PATTERN.sub(replace_hanja, text)


def _replace_stem_terms(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = match.group(1)
        return format_stem_label(STEMS_BY_HANJA[value]["kor"] if value in STEMS_BY_HANJA else value)

    text = _STEM_BEFORE_PATTERN.sub(replace, text)
    return _STEM_AFTER_PATTERN.sub(replace, text)


def _replace_branch_terms(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = match.group(1)
        return format_branch_label(BRANCHES_BY_HANJA[value]["kor"] if value in BRANCHES_BY_HANJA else value)

    text = _BRANCH_BEFORE_PATTERN.sub(replace, text)
    return _BRANCH_AFTER_PATTERN.sub(replace, text)
