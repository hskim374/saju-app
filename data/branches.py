"""Earthly branches metadata used by the saju calculator."""

BRANCHES = [
    {"kor": "자", "hanja": "子", "element": "water", "yin_yang": "yang"},
    {"kor": "축", "hanja": "丑", "element": "earth", "yin_yang": "yin"},
    {"kor": "인", "hanja": "寅", "element": "wood", "yin_yang": "yang"},
    {"kor": "묘", "hanja": "卯", "element": "wood", "yin_yang": "yin"},
    {"kor": "진", "hanja": "辰", "element": "earth", "yin_yang": "yang"},
    {"kor": "사", "hanja": "巳", "element": "fire", "yin_yang": "yin"},
    {"kor": "오", "hanja": "午", "element": "fire", "yin_yang": "yang"},
    {"kor": "미", "hanja": "未", "element": "earth", "yin_yang": "yin"},
    {"kor": "신", "hanja": "申", "element": "metal", "yin_yang": "yang"},
    {"kor": "유", "hanja": "酉", "element": "metal", "yin_yang": "yin"},
    {"kor": "술", "hanja": "戌", "element": "earth", "yin_yang": "yang"},
    {"kor": "해", "hanja": "亥", "element": "water", "yin_yang": "yin"},
]

BRANCHES_BY_KOR = {item["kor"]: item for item in BRANCHES}
BRANCHES_BY_HANJA = {item["hanja"]: item for item in BRANCHES}
