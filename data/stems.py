"""Heavenly stems metadata used by the saju calculator."""

STEMS = [
    {"kor": "갑", "hanja": "甲", "element": "wood", "yin_yang": "yang"},
    {"kor": "을", "hanja": "乙", "element": "wood", "yin_yang": "yin"},
    {"kor": "병", "hanja": "丙", "element": "fire", "yin_yang": "yang"},
    {"kor": "정", "hanja": "丁", "element": "fire", "yin_yang": "yin"},
    {"kor": "무", "hanja": "戊", "element": "earth", "yin_yang": "yang"},
    {"kor": "기", "hanja": "己", "element": "earth", "yin_yang": "yin"},
    {"kor": "경", "hanja": "庚", "element": "metal", "yin_yang": "yang"},
    {"kor": "신", "hanja": "辛", "element": "metal", "yin_yang": "yin"},
    {"kor": "임", "hanja": "壬", "element": "water", "yin_yang": "yang"},
    {"kor": "계", "hanja": "癸", "element": "water", "yin_yang": "yin"},
]

STEMS_BY_KOR = {item["kor"]: item for item in STEMS}
STEMS_BY_HANJA = {item["hanja"]: item for item in STEMS}
