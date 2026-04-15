"""Structure-level saju analysis used to avoid over-generic interpretations."""

from __future__ import annotations

from collections import Counter

from data.branches import BRANCHES_BY_HANJA, BRANCHES_BY_KOR
from data.hidden_stems import get_hidden_stems
from data.stems import STEMS_BY_HANJA, STEMS_BY_KOR
from services.ten_gods import calculate_ten_god_for_stem

SEASON_BY_MONTH_BRANCH = {
    "인": "spring",
    "묘": "spring",
    "진": "spring",
    "사": "summer",
    "오": "summer",
    "미": "summer",
    "신": "autumn",
    "유": "autumn",
    "술": "autumn",
    "해": "winter",
    "자": "winter",
    "축": "winter",
}

SEASON_LABELS = {
    "spring": "봄",
    "summer": "여름",
    "autumn": "가을",
    "winter": "겨울",
}

PILLAR_ROLES = {
    "year": "외부 환경",
    "month": "사회/직업 환경",
    "day": "본체/배우자",
    "hour": "결과/후반 인생",
}

ELEMENT_MAP = {
    **{stem: item["element"] for stem, item in STEMS_BY_KOR.items()},
    **{stem: item["element"] for stem, item in STEMS_BY_HANJA.items()},
    **{branch: item["element"] for branch, item in BRANCHES_BY_KOR.items()},
    **{branch: item["element"] for branch, item in BRANCHES_BY_HANJA.items()},
}

HIDDEN_STEMS = {
    BRANCHES_BY_KOR[branch]["hanja"]: [STEMS_BY_KOR[item["stem"]]["hanja"] for item in get_hidden_stems(branch)]
    for branch in BRANCHES_BY_KOR
}

SEASON_MAP = {
    BRANCHES_BY_KOR[branch]["hanja"]: season
    for branch, season in SEASON_BY_MONTH_BRANCH.items()
}

PATTERN_BY_TEN_GOD = {
    "식신": "식상격",
    "상관": "식상격",
    "편재": "재성격",
    "정재": "재성격",
    "편관": "관성격",
    "정관": "관성격",
    "편인": "인성격",
    "정인": "인성격",
    "비견": "비겁격",
    "겁재": "비겁격",
}

SUB_PATTERN_PREFIX = {
    "strong": "신강",
    "slightly_strong": "약간 신강",
    "balanced": "균형",
    "slightly_weak": "약간 신약",
    "weak": "신약",
}

SUB_PATTERN_SUFFIX = {
    "식상격": "식상 활용형",
    "재성격": "재성 운영형",
    "관성격": "관성 책임형",
    "인성격": "인성 보완형",
    "비겁격": "비겁 주도형",
    "균형격": "균형 운영형",
}

TEN_GOD_GROUP_BY_LABEL = {
    "식신": "식상",
    "상관": "식상",
    "편재": "재성",
    "정재": "재성",
    "편관": "관성",
    "정관": "관성",
    "편인": "인성",
    "정인": "인성",
    "비견": "비겁",
    "겁재": "비겁",
}

GENERATES = {
    "wood": "fire",
    "fire": "earth",
    "earth": "metal",
    "metal": "water",
    "water": "wood",
}

CONTROLS = {
    "wood": "earth",
    "fire": "metal",
    "earth": "water",
    "metal": "wood",
    "water": "fire",
}

SEASONAL_SUPPORT = {
    "spring": {"wood": 12, "fire": 8, "earth": 3, "metal": 1, "water": 5},
    "summer": {"wood": 6, "fire": 12, "earth": 7, "metal": 1, "water": 2},
    "autumn": {"wood": 2, "fire": 4, "earth": 7, "metal": 12, "water": 6},
    "winter": {"wood": 5, "fire": 2, "earth": 4, "metal": 6, "water": 12},
}


class StructureAnalyzer:
    """Three-layer PRD friendly structure analyzer (class interface)."""

    def analyze(self, saju: dict) -> dict:
        stems = self.extract_stems(saju)
        branches = self.extract_branches(saju)
        day_master = saju["day"]["stem"]
        month_branch = saju["month"]["branch"]
        season = self.get_season(month_branch)

        strength = self.calculate_strength(day_master, season, stems, branches)
        elements = self.calculate_elements(stems, branches)
        ten_gods = self.calculate_ten_gods(day_master, stems, branches)
        structure = self.detect_structure(day_master, ten_gods, strength)
        useful_gods = self.find_useful_gods(strength, elements)
        relations = self.detect_relations(stems, branches)
        pillar_roles = self.assign_pillar_roles()

        return {
            "day_master": day_master,
            "season": season,
            "month_branch": month_branch,
            "strength": strength,
            "five_elements": elements,
            "ten_gods": ten_gods,
            "structure": structure,
            "useful_gods": useful_gods,
            "relations": relations,
            "pillar_roles": pillar_roles,
        }

    def extract_stems(self, saju: dict) -> list[str]:
        stems: list[str] = []
        for role in ("year", "month", "day", "time"):
            pillar = saju.get(role)
            if pillar:
                stems.append(pillar["stem"])
        return stems

    def extract_branches(self, saju: dict) -> list[str]:
        branches: list[str] = []
        for role in ("year", "month", "day", "time"):
            pillar = saju.get(role)
            if pillar:
                branches.append(pillar["branch"])
        return branches

    def get_season(self, month_branch: str) -> str:
        branch_kor = self._to_kor_branch(month_branch)
        if branch_kor:
            return SEASON_BY_MONTH_BRANCH[branch_kor]
        return SEASON_MAP.get(month_branch, "spring")

    def calculate_strength(self, day_master: str, season: str, stems: list[str], branches: list[str]) -> dict:
        score = 0
        score += self.seasonal_score(day_master, season)

        for stem in stems:
            if self.same_element(day_master, stem):
                score += 5
            elif self.generates(stem, day_master):
                score += 3
            elif self.controls(stem, day_master):
                score -= 4

        for branch in branches:
            for hidden in get_hidden_stems(self._to_kor_branch(branch) or branch):
                hidden_stem = hidden["stem"]
                if self.same_element(day_master, hidden_stem):
                    score += 2
                elif self.generates(hidden_stem, day_master):
                    score += 1
                elif self.controls(hidden_stem, day_master):
                    score -= 1

        if score >= 70:
            label = "strong"
        elif score >= 50:
            label = "balanced"
        else:
            label = "weak"

        return {"score": score, "label": label}

    def calculate_elements(self, stems: list[str], branches: list[str]) -> dict:
        elements = {"wood": 0, "fire": 0, "earth": 0, "metal": 0, "water": 0}

        for stem in stems:
            element = ELEMENT_MAP.get(stem)
            if element:
                elements[element] += 2

        for branch in branches:
            element = ELEMENT_MAP.get(branch)
            if element:
                elements[element] += 3

            for hidden in get_hidden_stems(self._to_kor_branch(branch) or branch):
                hidden_element = ELEMENT_MAP.get(hidden["stem"])
                if hidden_element:
                    elements[hidden_element] += 1

        return elements

    def calculate_ten_gods(self, day_master: str, stems: list[str], branches: list[str]) -> dict:
        day_master_kor = self._to_kor_stem(day_master) or day_master
        visible: list[str] = []
        hidden: list[str] = []

        for stem in stems:
            stem_kor = self._to_kor_stem(stem) or stem
            ten_god = calculate_ten_god_for_stem(day_master_kor, stem_kor)
            if ten_god:
                visible.append(ten_god)

        for branch in branches:
            branch_kor = self._to_kor_branch(branch) or branch
            for item in get_hidden_stems(branch_kor):
                ten_god = calculate_ten_god_for_stem(day_master_kor, item["stem"])
                if ten_god:
                    hidden.append(ten_god)

        return {"visible": visible, "hidden": hidden}

    def detect_structure(self, day_master: str, ten_gods: dict, strength: dict) -> dict:
        del day_master  # future extension hook
        visible = ten_gods.get("visible", [])
        month_like = visible[1] if len(visible) >= 2 else (visible[0] if visible else "")
        primary_pattern = PATTERN_BY_TEN_GOD.get(month_like, "균형격")
        return {
            "primary_pattern": primary_pattern,
            "sub_pattern": _build_sub_pattern(
                strength["label"] if strength["label"] in SUB_PATTERN_PREFIX else "balanced",
                primary_pattern,
            ),
        }

    def find_useful_gods(self, strength: dict, elements: dict) -> dict:
        sorted_elements = sorted(elements.items(), key=lambda row: (-row[1], row[0]))
        weak_sorted = sorted(elements.items(), key=lambda row: (row[1], row[0]))
        yongshin = weak_sorted[0][0] if weak_sorted else "wood"
        kishin = [name for name, _ in sorted_elements[:2]]
        if strength["label"] == "weak":
            heeshin = [GENERATES[yongshin]]
        else:
            heeshin = [CONTROLS[yongshin]]
        return {"yongshin": yongshin, "heeshin": heeshin, "kishin": kishin}

    def detect_relations(self, stems: list[str], branches: list[str]) -> dict:
        del stems, branches  # placeholder for direct low-level relation engine hook
        return {
            "stem_combinations": [],
            "stem_clashes": [],
            "branch_combinations": [],
            "branch_clashes": [],
            "harms": [],
            "punishments": [],
            "breaks": [],
            "wonjin": [],
        }

    def assign_pillar_roles(self) -> dict:
        return PILLAR_ROLES.copy()

    def seasonal_score(self, day_master: str, season: str) -> int:
        element = ELEMENT_MAP.get(day_master)
        if not element:
            return 0
        return SEASONAL_SUPPORT.get(season, {}).get(element, 0)

    def same_element(self, left: str, right: str) -> bool:
        return ELEMENT_MAP.get(left) == ELEMENT_MAP.get(right)

    def generates(self, source: str, target: str) -> bool:
        source_element = ELEMENT_MAP.get(source)
        target_element = ELEMENT_MAP.get(target)
        if not source_element or not target_element:
            return False
        return GENERATES[source_element] == target_element

    def controls(self, source: str, target: str) -> bool:
        source_element = ELEMENT_MAP.get(source)
        target_element = ELEMENT_MAP.get(target)
        if not source_element or not target_element:
            return False
        return CONTROLS[source_element] == target_element

    def _to_kor_stem(self, value: str) -> str | None:
        if value in STEMS_BY_KOR:
            return value
        if value in STEMS_BY_HANJA:
            return STEMS_BY_HANJA[value]["kor"]
        return None

    def _to_kor_branch(self, value: str) -> str | None:
        if value in BRANCHES_BY_KOR:
            return value
        if value in BRANCHES_BY_HANJA:
            return BRANCHES_BY_HANJA[value]["kor"]
        return None


def analyze_structure(
    *,
    saju: dict,
    element_analysis: dict,
    ten_gods: dict,
    strength_analysis: dict,
    yongshin_analysis: dict,
    interactions: dict,
) -> dict:
    """Build structure-level signals and a chart signature key."""
    day_master = saju["day"]["stem"]
    month_branch = saju["month"]["branch"]
    season = SEASON_BY_MONTH_BRANCH[month_branch]
    season_label = SEASON_LABELS[season]

    month_visible_ten_god = ten_gods["ten_gods"].get("month")
    primary_pattern = PATTERN_BY_TEN_GOD.get(month_visible_ten_god, "균형격")
    sub_pattern = _build_sub_pattern(strength_analysis["label"], primary_pattern)
    top_visible_ten_gods = _top_visible_ten_gods(ten_gods)
    relationship_flags = _relationship_flags(interactions)

    signature = {
        "day_master": day_master,
        "month_branch": month_branch,
        "season": season,
        "strength_label": strength_analysis["label"],
        "primary_pattern": primary_pattern,
        "sub_pattern": sub_pattern,
        "yongshin": yongshin_analysis["primary_candidate"],
        "dominant_elements": tuple(sorted(element_analysis["dominant"])),
        "lacking_elements": tuple(sorted(element_analysis["weak"])),
        "top_visible_ten_gods": tuple(top_visible_ten_gods),
        "relationship_flags": tuple(sorted(relationship_flags)),
        "hour_theme": _hour_theme(ten_gods),
    }

    return {
        "day_master": day_master,
        "month_branch": month_branch,
        "season": season,
        "season_label": season_label,
        "primary_pattern": primary_pattern,
        "sub_pattern": sub_pattern,
        "top_visible_ten_gods": top_visible_ten_gods,
        "relationship_flags": relationship_flags,
        "pillar_roles": PILLAR_ROLES,
        "signature": signature,
        "signature_key": _signature_key(signature),
    }


def _build_sub_pattern(strength_label: str, primary_pattern: str) -> str:
    prefix = SUB_PATTERN_PREFIX.get(strength_label, "균형")
    suffix = SUB_PATTERN_SUFFIX.get(primary_pattern, "균형 운영형")
    return f"{prefix} {suffix}"


def _top_visible_ten_gods(ten_gods: dict) -> list[str]:
    counter: Counter[str] = Counter()
    visible = ten_gods["ten_gods"]
    for value in visible.values():
        if not value:
            continue
        counter[value] += 1
        counter[TEN_GOD_GROUP_BY_LABEL[value]] += 0.25

    if not counter:
        return []
    ranked = [item for item, _ in sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))]
    return ranked[:2]


def _relationship_flags(interactions: dict) -> list[str]:
    flags: set[str] = set()
    for item in interactions.get("natal", []):
        flags.add(item["type"])
    if not flags:
        flags.add("무충")
    return sorted(flags)


def _hour_theme(ten_gods: dict) -> str:
    hour_ten_god = ten_gods["ten_gods"].get("time")
    mapping = {
        "식신": "후반부 결과 생산형",
        "상관": "후반부 표현 확장형",
        "편재": "후반부 기회 포착형",
        "정재": "후반부 실속 관리형",
        "편관": "후반부 압박 대응형",
        "정관": "후반부 책임 강화형",
        "편인": "후반부 해석 보완형",
        "정인": "후반부 안정 회복형",
        "비견": "후반부 자율 주도형",
        "겁재": "후반부 경쟁 조율형",
    }
    return mapping.get(hour_ten_god, "후반부 균형 운영형")


def _signature_key(signature: dict) -> str:
    return "|".join(
        [
            signature["day_master"],
            signature["month_branch"],
            signature["season"],
            signature["strength_label"],
            signature["primary_pattern"],
            signature["sub_pattern"],
            signature["yongshin"],
            ",".join(signature["dominant_elements"]),
            ",".join(signature["lacking_elements"]),
            ",".join(signature["top_visible_ten_gods"]),
            ",".join(signature["relationship_flags"]),
            signature["hour_theme"],
        ]
    )
