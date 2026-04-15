"""Structure-aware report builder backed by a condition sentence DB."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from services.sentence_matcher import compose_section
from services.sentence_filter import load_filtered_sentences

SECTION_ORDER = [
    "core_structure",
    "personality",
    "career",
    "money",
    "relationship",
    "health",
    "luck_flow",
    "action_guide",
]

API_SECTION_ORDER = [
    "core_structure",
    "personality",
    "career",
    "money",
    "relationship",
    "health",
    "action_guide",
]

SECTION_FALLBACKS = {
    "core_structure": ["핵심 구조는 성향 한 줄보다 계절, 월지, 신강약, 용신 축을 함께 볼 때 더 정확합니다."],
    "personality": ["성향은 말투보다 판단 순서와 회복 방식에서 더 분명하게 드러나는 편입니다."],
    "career": ["일의 성패는 재능 자체보다 역할 분배와 운영 구조가 맞는지에서 갈리기 쉽습니다."],
    "money": ["재물은 수입 크기보다 유지 가능한 기준을 지키는지에서 체감 차이가 큽니다."],
    "relationship": ["관계는 감정 표현보다 속도와 간격을 맞추는 방식이 만족도를 크게 좌우합니다."],
    "health": ["건강은 단정 대신 생활 리듬과 회복 패턴을 먼저 점검하는 편이 안전합니다."],
    "luck_flow": ["운 흐름은 좋고 나쁨보다 내 구조와 맞는 기운이 들어오는 시기를 보는 것이 핵심입니다."],
    "action_guide": ["실전에서는 오늘, 이번 달, 올해의 기준을 분리해 관리하는 방식이 가장 안정적입니다."],
}

STRENGTH_HEADLINE_BY_LABEL = {
    "strong": [
        "주도력이 먼저 서는 강한 축의 사주",
        "판단 속도가 빠른 추진형 구조",
        "에너지를 밖으로 밀어내기 쉬운 강한 패턴",
        "기준을 직접 세우며 흐름을 이끄는 타입",
    ],
    "slightly_strong": [
        "추진력과 조정력이 함께 살아 있는 구조",
        "밀고 당기기 균형이 비교적 좋은 사주",
        "속도를 내되 관리도 가능한 중강형 패턴",
        "주도와 협업을 병행하기 쉬운 흐름",
    ],
    "balanced": [
        "한쪽으로 과도하게 쏠리지 않은 균형형 사주",
        "상황에 맞춰 전략을 바꾸기 쉬운 중립 구조",
        "안정과 확장을 조절하기 쉬운 균형 패턴",
        "무리하지 않으면 성과가 꾸준히 누적되는 타입",
    ],
    "slightly_weak": [
        "환경의 질이 결과를 크게 좌우하는 약신형 구조",
        "속도보다 운영 방식이 중요한 신약 경향의 사주",
        "무리한 확장보다 기준 정비가 먼저인 패턴",
        "자원 보강이 성과 품질을 좌우하는 흐름",
    ],
    "weak": [
        "작은 소모가 누적되기 쉬운 신약 중심의 구조",
        "에너지 관리가 핵심인 약신형 사주",
        "기회보다 체력과 리듬 관리가 우선인 패턴",
        "기준 없이 확장하면 피로가 커지기 쉬운 흐름",
    ],
}

PATTERN_HEADLINE_BY_KEY = {
    "식상격": [
        "표현과 결과 생산 능력이 핵심 축으로 작동합니다",
        "아이디어를 실행으로 바꾸는 힘이 구조의 중심입니다",
        "산출물과 성과를 만드는 장면에서 장점이 뚜렷합니다",
    ],
    "재성격": [
        "실속과 수익 구조를 읽는 감각이 중심 축입니다",
        "돈의 흐름을 설계하는 현실 감각이 강점으로 작동합니다",
        "성과를 쌓아 자산으로 전환하는 패턴이 핵심입니다",
    ],
    "관성격": [
        "책임과 기준을 세우는 힘이 구조의 중심입니다",
        "역할과 규칙을 정리할 때 강점이 크게 살아납니다",
        "조직 안에서 신뢰를 쌓는 방식이 성과로 이어집니다",
    ],
    "인성격": [
        "해석과 학습을 통한 보완력이 핵심 축으로 작동합니다",
        "정보를 정리해 판단 정확도를 높이는 구조가 강합니다",
        "내실을 다진 뒤 확장하는 방식이 잘 맞는 패턴입니다",
    ],
    "비겁격": [
        "자율성과 실행 주도권이 성과의 핵심 축입니다",
        "협업과 경쟁을 함께 다루는 장면에서 강점이 드러납니다",
        "판을 직접 움직일 때 결과 차이가 크게 납니다",
    ],
    "균형격": [
        "상황별로 운영 방식을 바꾸는 유연성이 핵심입니다",
        "한 축에 과하게 묶이지 않아 선택 폭이 넓은 구조입니다",
        "리듬을 안정적으로 유지할수록 성과가 누적됩니다",
    ],
}

FLOW_HEADLINE_CONFLICT = [
    "원국 충돌 신호가 있어 관계와 의사결정 속도 조절이 중요합니다.",
    "강한 충돌 구간이 감지되어 우선순위 정리가 성패를 가릅니다.",
    "부딪힘 신호가 있어 일정과 대화 간격을 미리 관리하는 편이 안전합니다.",
]

FLOW_HEADLINE_HARMONY = [
    "연결 신호가 살아 있어 협업과 조율에서 회복력이 좋습니다.",
    "완화 흐름이 있어 갈등을 풀어 성과로 전환하기 쉬운 구간입니다.",
    "합의 리듬이 붙는 구조라 사람과 조건을 함께 보며 가면 유리합니다.",
]

FLOW_HEADLINE_MOVEMENT = [
    "역마 신호가 있어 자리 이동·역할 전환 같은 변화 대응력이 중요합니다.",
    "변화성이 강한 흐름이라 기존 방식 고정보다 기민한 조정이 유리합니다.",
]

FLOW_HEADLINE_RELATIONSHIP = [
    "도화 흐름이 작동해 대인 반응과 노출 관리가 결과 품질을 좌우합니다.",
    "관계 주목도가 높아지는 구간이라 말의 강약 조절이 특히 중요합니다.",
]

FLOW_HEADLINE_FOCUS = [
    "화개 흐름이 있어 혼자 정리하는 시간 확보가 완성도를 높입니다.",
    "집중 신호가 살아 있어 마무리 품질 관리에서 강점이 드러납니다.",
]

FLOW_HEADLINE_DEFAULT = [
    "과열보다 리듬 유지에 초점을 두면 안정적인 결과를 만들 수 있습니다.",
    "속도와 안정의 균형을 맞출 때 같은 조건에서도 결과 차이가 커집니다.",
    "오늘·주간·월간 기준을 분리해 운영하면 변동성 대응이 쉬워집니다.",
]


def build_structured_report(analysis_context: dict, signals: dict) -> dict:
    """Build a structure-aware report payload from analysis context + signals."""
    analysis = _build_analysis_payload(analysis_context, signals)
    sentence_db = _load_sentence_db()
    seed = _seed_from_signature(analysis_context["structure"]["signature_key"])

    sections = {}
    match_logs: dict[str, dict] = {}
    for index, section_name in enumerate(SECTION_ORDER):
        lines, matched_rows, candidate_count = compose_section(
            section_name,
            analysis,
            sentence_db,
            seed=seed + index * 17,
            return_rows=True,
        )
        used_fallback = not bool(lines)
        sections[section_name] = lines if lines else SECTION_FALLBACKS[section_name]
        match_logs[section_name] = {
            "matched_count": len(matched_rows),
            "matched_ids": [str(row.get("id", "")) for row in matched_rows if row.get("id")],
            "candidate_count": candidate_count,
            "used_fallback": used_fallback,
        }

    headline = _build_headline(analysis_context)
    summary = _build_summary_sections(sections, analysis_context)

    return {
        "headline": headline,
        "summary": summary,
        "sections": sections,
        "match_logs": match_logs,
    }


def _build_analysis_payload(analysis_context: dict, signals: dict) -> dict:
    structure = analysis_context["structure"]
    strength = analysis_context["strength"]
    flags = analysis_context["flags"]
    dominant_elements = analysis_context["elements"]["dominant_kor"]
    lacking_elements = analysis_context["elements"]["weak_kor"]
    dominant_element = analysis_context["elements"]["dominant"][0] if analysis_context["elements"]["dominant"] else ""
    lacking_element = analysis_context["elements"]["weak"][0] if analysis_context["elements"]["weak"] else ""
    relationship_flags = structure["relationship_flags"]
    return {
        "day_master": structure["day_master"],
        "month_branch": structure["month_branch"],
        "season": structure["season"],
        "strength_label": strength["label"],
        "primary_pattern": structure["primary_pattern"],
        "sub_pattern": structure["sub_pattern"],
        "yongshin": analysis_context["yongshin"]["display"]["primary"],
        "yongshin_element": analysis_context["yongshin"]["primary_candidate"],
        "dominant_elements": dominant_elements,
        "lacking_elements": lacking_elements,
        "dominant_element": dominant_element,
        "lacking_element": lacking_element,
        "top_visible_ten_gods": structure["top_visible_ten_gods"],
        "relationship_flags": relationship_flags,
        "has_clash": "충" in relationship_flags or flags["has_natal_conflict"],
        "branch_clash": "충" in relationship_flags,
        "branch_harm": "해" in relationship_flags,
        "branch_punishment": "형" in relationship_flags,
        "branch_break": "파" in relationship_flags,
        "branch_wonjin": "원진" in relationship_flags,
        "special_star_tags": analysis_context["special_stars"]["tags"],
        "hour_theme": structure["signature"]["hour_theme"],
        "has_luck_pressure": flags["has_luck_pressure"],
        "has_natal_conflict": flags["has_natal_conflict"],
        "has_natal_harmony": flags["has_natal_harmony"],
        "needs_resource_support": flags["needs_resource_support"],
        "needs_output_release": flags["needs_output_release"],
        "wealth_flow_open": flags["wealth_flow_open"],
        "officer_pressure_high": flags["officer_pressure_high"],
        "signals_core": signals.get("core", []),
    }


def _build_headline(analysis_context: dict) -> str:
    structure = analysis_context["structure"]
    strength = analysis_context["strength"]
    flags = analysis_context["flags"]
    special_stars = analysis_context["special_stars"]
    seed = _seed_from_signature(structure["signature_key"])

    strength_lead = _pick(STRENGTH_HEADLINE_BY_LABEL.get(strength["label"], STRENGTH_HEADLINE_BY_LABEL["balanced"]), seed + 11)
    pattern_core = _pick(PATTERN_HEADLINE_BY_KEY.get(structure["primary_pattern"], PATTERN_HEADLINE_BY_KEY["균형격"]), seed + 23)

    flow_candidates: list[str] = []
    if flags["has_natal_conflict"]:
        flow_candidates.extend(FLOW_HEADLINE_CONFLICT)
    if flags["has_natal_harmony"]:
        flow_candidates.extend(FLOW_HEADLINE_HARMONY)
    if special_stars.get("has_movement_star"):
        flow_candidates.extend(FLOW_HEADLINE_MOVEMENT)
    if special_stars.get("has_relationship_star"):
        flow_candidates.extend(FLOW_HEADLINE_RELATIONSHIP)
    if special_stars.get("has_focus_star"):
        flow_candidates.extend(FLOW_HEADLINE_FOCUS)
    if not flow_candidates:
        flow_candidates = FLOW_HEADLINE_DEFAULT

    flow_note = _pick(flow_candidates, seed + 37)
    return f"{strength_lead}, {pattern_core}. {flow_note}"


def _build_summary_sections(sections: dict, analysis_context: dict) -> list[str]:
    structure = analysis_context["structure"]
    yongshin = analysis_context["yongshin"]["display"]
    flags = analysis_context["flags"]
    special_stars = analysis_context["special_stars"]
    seed = _seed_from_signature(structure["signature_key"])

    summary: list[str] = []

    line_one_candidates = [
        f"{structure['season_label']} 배경의 {structure['sub_pattern']} 구조라 같은 일간 안에서도 반응 결이 분명히 갈립니다.",
        f"핵심 패턴은 {structure['sub_pattern']}이며 월지 {structure['month_branch']} 환경의 영향을 강하게 받는 편입니다.",
        f"{structure['primary_pattern']} 중심 구조에 계절 보정이 더해져 해석의 우선순위가 선명하게 잡힙니다.",
    ]
    _append_unique(summary, _pick(line_one_candidates, seed + 41))

    line_two_candidates: list[str] = []
    if flags["needs_resource_support"]:
        line_two_candidates.extend(
            [
                f"용신 기준은 {yongshin['primary']} 쪽 보강이며, 보조로 {yongshin['secondary']} 흐름을 묶으면 흔들림이 줄어듭니다.",
                f"자원 보강형 운용이 맞아 {yongshin['primary']} 기준을 먼저 세우는 것이 판단 오차를 줄입니다.",
            ]
        )
    if flags["needs_output_release"]:
        line_two_candidates.extend(
            [
                "실행·표현 출구를 열어야 운용 효율이 올라가므로 미루던 일을 작은 단위로 끊어내는 편이 좋습니다.",
                "정리만 길어지면 피로가 누적되기 쉬워 완료 기준을 먼저 확정하는 운영이 유리합니다.",
            ]
        )
    if flags["officer_pressure_high"]:
        line_two_candidates.extend(
            [
                "관성 압력이 높게 감지되어 책임 분배와 마감 우선순위를 명확히 두는 편이 안전합니다.",
                "기준과 규칙이 강하게 들어오는 구조라 완성도보다 일정 관리 실패를 먼저 막아야 합니다.",
            ]
        )
    if flags["wealth_flow_open"]:
        line_two_candidates.extend(
            [
                "재물 흐름이 열리는 구간이라 벌기보다 누수 차단과 유지 전략을 같이 가져가는 편이 효율적입니다.",
                "수익 기회는 열리되 변동성도 커질 수 있어 기준 없는 확장보다 선별 운용이 맞습니다.",
            ]
        )
    if special_stars.get("tags"):
        line_two_candidates.extend(
            [
                f"신살 흐름은 {', '.join(special_stars['tags'])} 축이 감지되어 일상 리듬 관리 방식에 체감 차이가 큽니다.",
                f"{', '.join(special_stars['tags'])} 신호가 동시에 보여 관계·변화·집중 축을 나눠 관리하는 편이 효과적입니다.",
            ]
        )
    if not line_two_candidates:
        line_two_candidates = [
            f"운용 기준은 {yongshin['primary']} 중심으로 두고 과열보다 페이스 유지에 초점을 맞추는 편이 안정적입니다.",
            "핵심은 큰 결정보다 반복 업무 품질을 먼저 올리는 방식으로 누적 성과를 만드는 것입니다.",
        ]
    _append_unique(summary, _pick(line_two_candidates, seed + 53))

    line_three_candidates = [
        f"후반 운영 테마는 {structure['signature']['hour_theme']} 쪽으로 읽혀, 마무리 품질을 의식할수록 결과가 좋아집니다.",
        "오늘·주간·월간 기준을 분리해 관리하면 변동성 구간에서도 실행력이 안정적으로 유지됩니다.",
        "실전에서는 한 번에 크게 바꾸기보다 작은 완료 단위를 누적하는 방식이 가장 재현성이 높습니다.",
    ]
    _append_unique(summary, _pick(line_three_candidates, seed + 67))

    for section_name in ["core_structure", "personality", "career", "money"]:
        lines = sections.get(section_name, [])
        if not lines:
            continue
        _append_unique(summary, lines[0])
        if len(summary) >= 5:
            break

    return summary[:3]


def _seed_from_signature(signature_key: str) -> int:
    return sum(ord(char) for char in signature_key)


def _pick(options: list[str], seed: int) -> str:
    if not options:
        return ""
    return options[seed % len(options)]


def _append_unique(target: list[str], line: str) -> None:
    if not line:
        return
    if line in target:
        return
    target.append(line)


class ReportBuilder:
    """Simple category report assembler for API consumers."""

    def __init__(self, matcher, limit_per_category: int = 5):
        self.matcher = matcher
        self.limit_per_category = limit_per_category

    def build(self, analysis: dict) -> dict:
        match_context = self._normalize_analysis(analysis)
        sections: dict[str, list[str]] = {}
        for category in API_SECTION_ORDER:
            matched = self.matcher.match(analysis=match_context, category=category, limit=self.limit_per_category)
            sections[category] = [item["text"] for item in matched if item.get("text")]
        return sections

    def _normalize_analysis(self, analysis: dict) -> dict:
        if "strength_label" in analysis:
            return analysis

        five_elements = analysis.get("five_elements", {})
        ranked_desc = sorted(five_elements.items(), key=lambda row: (-row[1], row[0])) if five_elements else []
        ranked_asc = sorted(five_elements.items(), key=lambda row: (row[1], row[0])) if five_elements else []

        relations = analysis.get("relations", {})
        has_clash = bool(relations.get("branch_clashes") or relations.get("stem_clashes"))

        return {
            "day_master": analysis.get("day_master", ""),
            "season": analysis.get("season", ""),
            "strength_label": analysis.get("strength", {}).get("label", ""),
            "primary_pattern": analysis.get("structure", {}).get("primary_pattern", ""),
            "yongshin": analysis.get("useful_gods", {}).get("yongshin", ""),
            "yongshin_element": analysis.get("useful_gods", {}).get("yongshin", ""),
            "dominant_element": ranked_desc[0][0] if ranked_desc else "",
            "lacking_element": ranked_asc[0][0] if ranked_asc else "",
            "has_clash": has_clash,
        }


def clear_sentence_db_cache() -> None:
    _load_sentence_db.cache_clear()


@lru_cache(maxsize=1)
def _load_sentence_db() -> list[dict]:
    filtered_path = Path("data/sentences.json")
    if filtered_path.exists():
        with filtered_path.open(encoding="utf-8") as file:
            payload = json.load(file)
        if isinstance(payload, list) and payload:
            return payload
    return load_filtered_sentences()
