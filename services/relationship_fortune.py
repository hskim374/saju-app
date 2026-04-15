"""Relationship and marriage fortune interpretation."""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock

from data.day_pillar_sentences import get_day_pillar_sentence_options
from data.month_ten_god_specialized import MONTH_TEN_GOD_RELATION_LINES
from services.analysis_sentence_store import load_analysis_sentences
from services.interpretation_engine import build_relationship_section
from services.interpretation_templates import RELATIONSHIP_ACTION
from services.ten_gods import calculate_ten_gods

ELEMENT_KOR_ONLY = {
    "wood": "목",
    "fire": "화",
    "earth": "토",
    "metal": "금",
    "water": "수",
}


def _relationship_strength_scene_line(strength: dict) -> str:
    label = strength["label"]
    if label in {"weak", "slightly_weak"}:
        return "관계에서는 감정이 커져도 템포를 늦추고 회복할 간격을 남기는 편이 더 안정적입니다."
    if label in {"strong", "slightly_strong"}:
        return "관계에서는 한쪽 감정으로 몰아붙이기 쉬워, 표현 수위와 속도를 같이 조절하는 편이 좋습니다."
    return "관계에서는 감정과 현실 조건을 같이 보며 천천히 맞추는 편이 흐름을 지키기 쉽습니다."


def _relationship_yongshin_scene_line(yongshin: dict) -> str:
    primary_map = {
        "wood": "답을 하나로 빨리 닫기보다 다음 대화의 여지를 조금 열어 두는",
        "fire": "마음이 보일 때 필요한 만큼만 분명하게 표현하는",
        "earth": "좋아도 버틸 수 있는 속도와 생활 리듬을 먼저 맞추는",
        "metal": "관계 기준과 선을 먼저 분명히 하는",
        "water": "좋아도 바로 확정하지 않고 흐름을 한 번 더 보는",
    }
    secondary_map = {
        "wood": "다음 만남의 여지를 남기는",
        "fire": "표현 강도를 한 번 다듬는",
        "earth": "무리 없는 속도를 다시 확인하는",
        "metal": "세부 기준을 차분히 정리하는",
        "water": "결론을 서두르지 않는",
    }
    primary_phrase = primary_map.get(yongshin["primary_candidate"], "먼저 기준을 세우는")
    secondary_phrase = secondary_map.get(yongshin["secondary_candidate"], "한 번 더 살펴보는")
    return f"관계에서는 {primary_phrase} 쪽으로 움직이고, {secondary_phrase} 정도의 여지도 같이 챙기는 편이 좋습니다."


def _relationship_hidden_focus_line(group: str | None) -> str:
    mapping = {
        "비겁": "관계에서는 내 기준과 거리 조절 문제가 먼저 올라와, 가까워지는 속도를 빨리 나누는 편이 마음 소모를 줄이기 쉽습니다.",
        "식상": "관계에서는 말보다 표현 순서와 실제 행동이 먼저 보이기 쉬워, 약속과 행동이 감정보다 더 크게 읽힐 수 있습니다.",
        "재성": "관계에서는 감정보다 현실 조건과 유지 가능성을 먼저 따지는 반응이 올라와, 오래 갈 수 있는지를 빨리 보게 될 수 있습니다.",
        "관성": "관계에서는 책임감과 일관성을 먼저 보게 돼, 속도보다 신뢰 기준을 맞추는 편이 훨씬 중요해질 수 있습니다.",
        "인성": "관계에서는 서두르기보다 상대 의도와 분위기를 다시 확인하고 싶은 마음이 강해져, 한 템포 늦춘 판단이 더 잘 맞을 수 있습니다.",
    }
    return mapping.get(group or "", "")


def _relationship_action_support_line(flags: dict, yongshin: dict) -> str:
    primary_map = {
        "wood": "답을 하나로 빨리 닫지 않는",
        "fire": "필요한 표현은 분명히 하는",
        "earth": "버틸 수 있는 속도와 생활 리듬을 먼저 맞추는",
        "metal": "관계 기준과 선을 먼저 정리하는",
        "water": "좋아도 한 번 더 살피는",
    }
    primary_phrase = primary_map.get(yongshin["primary_candidate"], "먼저 기준을 세우는")
    if flags["needs_resource_support"]:
        return "관계는 감정보다 안정과 신뢰를 먼저 쌓는 쪽이 더 잘 맞습니다."
    if flags["needs_output_release"]:
        return "관계는 생각만 길게 두기보다 필요한 표현은 제때 꺼내는 편이 좋습니다."
    return f"관계는 한쪽 감정으로 몰리지 않게 {primary_phrase} 편이 흐름을 덜 흔듭니다."


def _normalize_relationship_support_line(line: str) -> str:
    normalized = line.strip()
    for prefix in ("그래서, ", "결국, ", "여기서 중요한 건, ", "다만, ", "특히, ", "대신, "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    replacements = (
        ("실무적으로 풀면 ", ""),
        ("월간 십성 보정으로 보면 ", ""),
        ("월간 비견이 서 있으면 ", ""),
        ("월간 겁재가 서 있으면 ", ""),
        ("월간 식신이 서 있으면 ", ""),
        ("월간 상관이 서 있으면 ", ""),
        ("월간 편재가 서 있으면 ", ""),
        ("월간 정재가 서 있으면 ", ""),
        ("월간 편관이 서 있으면 ", ""),
        ("월간 정관이 서 있으면 ", ""),
        ("월간 편인이 서 있으면 ", ""),
        ("월간 정인이 서 있으면 ", ""),
        ("이 흐름을 성격 쪽으로 풀면 ", ""),
        ("성향 보정으로 읽으면 ", ""),
    )
    for source, target in replacements:
        if normalized.startswith(source):
            normalized = target + normalized[len(source):]
            break
    return normalized


def _strip_relationship_day_pillar_line(line: str) -> str:
    normalized = line.strip()
    prefixes = (
        "가까워질지 한발 물러설지 정해야 하는 장면에서는 ",
        "연락을 이어 갈지 멈출지 고민하는 순간에는 ",
        "호감이 있어도 속도를 바로 올리기 어려운 장면에서는 ",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return normalized

RELATIONSHIP_RULES = {
    "wealth": {
        "trend": "인연 유입",
        "strong": "인연운이 강하게 들어오지만 속도보다 안정성을 먼저 확인해야 하는 흐름입니다.",
        "medium": "사람 흐름이 열리되 감정과 현실 조건을 함께 보는 편이 좋은 흐름입니다.",
        "light": "관계의 문이 조금씩 열리므로 자연스러운 접점을 넓히는 편이 좋습니다.",
        "strengths": [
            "새로운 만남이나 관계로 이어질 외부 접점이 늘어날 수 있습니다.",
            "호감이 생기더라도 현실 조건을 같이 보는 태도가 오히려 관계를 안정시킵니다.",
        ],
        "warnings": [
            "감정이 앞서면 속도가 빨라질 수 있어 결정은 한 박자 늦추는 편이 좋습니다.",
        ],
    },
    "officer": {
        "trend": "안정/판단",
        "strong": "관계의 방향이 또렷해지지만 기준을 분명히 세워야 흐름이 살아나는 시기입니다.",
        "medium": "인연보다 관계의 안정성과 책임감이 더 중요해지는 흐름입니다.",
        "light": "천천히 관계의 기준을 정리하면 흐름이 부드럽게 이어질 수 있습니다.",
        "strengths": [
            "책임감 있는 인연이나 관계 정리가 눈에 들어오기 쉬운 시기입니다.",
            "관계의 기준을 분명히 할수록 안정성이 높아집니다.",
        ],
        "warnings": [
            "상대의 속도보다 자신의 판단 기준을 먼저 확인하는 편이 좋습니다.",
        ],
    },
    "mixed": {
        "trend": "재정비",
        "strong": "관계는 유지보다 재정비 흐름이 강해 감정의 속도와 거리 조절이 핵심이 됩니다.",
        "medium": "새 인연보다 소통 방식과 거리 조절을 손보는 쪽에 무게가 실립니다.",
        "light": "관계 흐름은 서서히 움직이므로 대화의 톤을 정리하는 편이 좋습니다.",
        "strengths": [
            "대화 방식과 거리 조절을 정리하면 관계 흐름이 한결 부드러워질 수 있습니다.",
        ],
        "warnings": [
            "감정 기복이 큰 날에는 결론을 서두르지 않는 편이 안전합니다.",
        ],
    },
}

DAY_STEM_RELATION_LINES = {
    "갑": "관계 방향을 빨리 정해야 하는 장면에서는 태도와 기준이 맞는지를 먼저 보는 편입니다.",
    "을": "상대에게 맞추는 장면에서도 속으로는 리듬과 안전선을 꽤 오래 보는 편입니다.",
    "병": "호감이 생겼을 때는 표현과 반응이 비교적 빠르게 밖으로 드러나기 쉬운 편입니다.",
    "정": "분위기가 미묘할수록 타이밍을 먼저 보고 감정을 조심스럽게 꺼내는 편입니다.",
    "무": "좋아도 오래 갈 수 있는지와 현실성이 맞는지를 먼저 따지는 편입니다.",
    "기": "상대 상황과 내 현실을 같이 보며 무리 없는 속도로 맞추려는 편입니다.",
    "경": "애매한 상태를 오래 두기보다 기준과 선을 분명히 하고 싶어지는 장면이 많습니다.",
    "신": "표현은 절제돼도 세부적인 태도와 균형을 꽤 오래 보는 편입니다.",
    "임": "감정 하나보다 전체 흐름과 가능성을 넓게 읽는 쪽으로 움직이기 쉽습니다.",
    "계": "겉표현보다 분위기와 맥락을 더 오래 읽으며 판단하는 편입니다.",
}

MONTH_BRANCH_RELATION_LINES = {
    "자": "관계에서도 먼저 흐름과 분위기를 읽어야 마음이 놓이는 장면이 많습니다.",
    "축": "천천히 쌓이는 신뢰와 버틸 수 있는 생활 감각을 더 중요하게 봅니다.",
    "인": "정체된 상태보다 앞으로 나아가는 느낌이 있어야 힘이 붙기 쉽습니다.",
    "묘": "감정의 세기보다 관계 리듬과 거리 조절의 부드러움이 더 중요하게 작동합니다.",
    "진": "여러 조건을 같이 놓고 현실적으로 맞는지를 따지는 편입니다.",
    "사": "반응 속도가 빨라질 수 있어 감정이 달아오를 때 페이스 조절이 중요합니다.",
    "오": "정적인 흐름보다 살아 있는 반응과 존재감이 보일 때 더 끌리기 쉽습니다.",
    "미": "겉으로 빠르지 않아도 오래 갈 수 있는 안정감이 더 중요합니다.",
    "신": "말보다 태도, 약속, 선 긋기 같은 기준을 더 민감하게 보는 편입니다.",
    "유": "가까워질수록 세부 태도와 완성도를 보며 관계 판단을 더 섬세하게 하는 편입니다.",
    "술": "책임감과 일관성이 확인될 때 비로소 마음을 더 여는 편입니다.",
    "해": "서두르기보다 여지를 두고 천천히 보는 쪽이 더 자연스럽습니다.",
}

TIME_BRANCH_RELATION_LINES = {
    "자": "시지에 자수가 놓이면 가까운 관계일수록 속으로 생각이 길어져 결론을 늦추는 편입니다.",
    "축": "시지에 축토가 놓이면 친밀한 관계에서도 급히 열기보다 안에서 정리한 뒤 표현하는 편입니다.",
    "인": "시지에 인목이 놓이면 시간이 갈수록 관계에서 더 넓은 가능성과 방향을 보고 싶어질 수 있습니다.",
    "묘": "시지에 묘목이 놓이면 가까운 관계일수록 거리 조절과 부드러운 호흡이 중요하게 작동합니다.",
    "진": "시지에 진토가 놓이면 친한 사이일수록 여러 조건을 현실적으로 비교하며 쉽게 확정하지 않는 편입니다.",
    "사": "시지에 사화가 놓이면 가까운 사람 앞에서는 표현과 반응이 더 빨라질 수 있습니다.",
    "오": "시지에 오화가 놓이면 친밀한 관계에서 감정이 붙었을 때 속도와 열기가 크게 올라오기 쉽습니다.",
    "미": "시지에 미토가 놓이면 시간이 갈수록 관계에서도 오래 갈 수 있는 안정감을 더 중요하게 봅니다.",
    "신": "시지에 신금이 놓이면 가까운 관계일수록 선과 기준을 더 분명히 하고 싶어지는 편입니다.",
    "유": "시지에 유금이 놓이면 친밀한 사이에서도 사소한 태도 차이를 오래 기억하는 편입니다.",
    "술": "시지에 술토가 놓이면 가까운 관계일수록 책임감과 신뢰 문제를 더 무겁게 보는 편입니다.",
    "해": "시지에 해수가 놓이면 친밀한 관계에서는 결론보다 여지를 남겨 두는 태도가 먼저 나올 수 있습니다.",
}

RELATIONSHIP_SPEED_WARNINGS = {
    "사": "감정이 붙었을 때 속도가 빨라질 수 있어 결정은 하루 정도 늦추는 편이 좋습니다.",
    "오": "관계 열기가 올라올수록 말의 수위와 연락 빈도를 같이 조절하는 편이 안정적입니다.",
    "자": "생각이 길어질수록 타이밍이 늦어질 수 있어 기준을 먼저 정리하는 편이 좋습니다.",
    "해": "여지를 오래 두는 성향이 강해지면 상대에게 애매하게 보일 수 있어 표현 시점을 잡는 편이 좋습니다.",
}

RELATIONSHIP_PROFILE_HEADLINES = {
    "slow_trust": "관계는 빠른 감정보다 천천히 쌓이는 신뢰에서 차이가 나는 타입입니다.",
    "pace_adjuster": "관계는 감정 크기보다 속도와 거리 조절에서 결과가 갈리는 타입입니다.",
    "boundary_first": "관계는 호감보다 기준과 선이 분명해야 편안해지는 타입입니다.",
    "observer": "관계는 표현보다 관찰과 맥락 읽기가 먼저 작동하는 타입입니다.",
    "expressive": "관계는 마음이 움직이면 반응과 표현이 빨라지기 쉬운 타입입니다.",
    "balanced_connector": "관계는 상대와의 호흡을 맞추며 조율하는 장점이 큰 타입입니다.",
}

RELATIONSHIP_PROFILE_SUMMARIES = {
    "slow_trust": "좋아도 바로 깊게 들어가기보다 시간이 지나며 신뢰가 쌓일 때 관계가 안정되기 쉽습니다.",
    "pace_adjuster": "관계가 틀어지는 이유도 감정보다 속도 차이에서 시작될 가능성이 큽니다.",
    "boundary_first": "애매한 상태를 오래 두기보다 선과 기준이 정리될 때 마음이 더 편해지기 쉽습니다.",
    "observer": "호감이 있어도 먼저 분위기와 흐름을 읽으며 타이밍을 보는 쪽으로 움직일 가능성이 큽니다.",
    "expressive": "감정이 붙을 때 속도와 열기가 함께 올라오기 쉬워 호흡 조절이 중요합니다.",
    "balanced_connector": "서로의 리듬을 맞추는 힘은 좋지만, 내 속도를 잃지 않는 기준도 같이 필요합니다.",
}

RELATIONSHIP_PROFILE_ADVICE = {
    "slow_trust": [
        "좋아도 빠르게 확정하지 말고 서로의 생활 리듬이 맞는지 먼저 보는 편이 좋습니다.",
        "호감이 생겨도 관계 속도를 천천히 올리며 생활 패턴이 맞는지 확인하는 편이 안정적입니다.",
        "초반에는 대화 빈도보다 약속 이행을 보며 신뢰를 쌓는 방식이 더 잘 맞습니다.",
        "감정이 좋아도 결론을 서두르지 말고 두세 번의 만남에서 일관성을 확인하는 편이 좋습니다.",
        "관계를 깊게 가져가기 전 연락 간격과 만남 리듬을 먼저 맞추는 편이 유리합니다.",
        "표현은 따뜻하게 하되 확정은 늦추고 현실 조건을 체크하는 습관이 도움이 됩니다.",
    ],
    "pace_adjuster": [
        "감정이 커질수록 연락 빈도와 가까워지는 속도를 의식적으로 늦추는 편이 좋습니다.",
        "좋아도 바로 일정을 늘리기보다 주 1~2회처럼 간격을 고정해 보는 편이 안정적입니다.",
        "관계가 빨라질수록 오해도 빨라질 수 있어 확인 대화를 짧게 자주 넣는 편이 좋습니다.",
        "표현이 앞서기 쉬운 시기라 결론보다 속도 조절 규칙을 먼저 세우는 편이 유리합니다.",
        "연락이 잦아질수록 답장 속도보다 대화 품질을 맞추는 쪽이 관계 피로를 줄입니다.",
        "가까워지는 흐름이 와도 만남 횟수보다 관계 리듬의 안정성을 먼저 챙기는 편이 좋습니다.",
    ],
    "boundary_first": [
        "상대에게 맞추기 전에 내가 편한 거리와 기준을 먼저 설명하는 편이 더 안정적입니다.",
        "호감이 있어도 가능한 시간·연락 방식·관계 속도를 먼저 정리해 두는 편이 좋습니다.",
        "애매한 상태를 길게 끌기보다 내 기준을 짧게 공유해 오해를 줄이는 편이 유리합니다.",
        "초반에 선을 분명히 하면 이후 감정이 커져도 관계가 흔들릴 가능성을 줄일 수 있습니다.",
        "관계가 좋아도 무리한 맞춤보다 내 일상 리듬을 지키는 기준을 먼저 두는 편이 좋습니다.",
        "상대 기대치에 맞추기 전에 내가 감당 가능한 범위를 먼저 밝히는 편이 안정적입니다.",
    ],
    "observer": [
        "계속 관찰만 하기보다 표현 시점을 하나 정해 두는 편이 관계 흐름을 놓치지 않는 데 도움이 됩니다.",
        "생각이 길어질수록 타이밍을 놓치기 쉬우니 답을 미루는 한도를 정해 두는 편이 좋습니다.",
        "상대 반응을 충분히 보되 결정은 기한을 두고 내리는 방식이 관계 안정에 유리합니다.",
        "관찰이 강점이지만 무반응으로 보일 수 있어 짧은 표현 한 번은 의식적으로 넣는 편이 좋습니다.",
        "타이밍이 중요하니 완벽한 확신보다 70% 확신 시점에 의사표현을 시작하는 편이 도움이 됩니다.",
        "분위기를 읽는 힘을 살리되 핵심 질문은 먼저 던져 관계 방향을 분명히 하는 편이 좋습니다.",
    ],
    "expressive": [
        "호감이 커질수록 결론을 하루 정도 늦추고 말의 강약을 조절하는 편이 좋습니다.",
        "감정 표현이 빠른 장점이 있어도 중요한 약속은 하루 유예 후 확정하는 편이 안정적입니다.",
        "좋은 흐름일수록 말의 세기보다 순서를 조절하면 관계 만족도가 더 높아질 수 있습니다.",
        "표현이 앞설 때는 기대치를 먼저 맞추고 감정 수위를 천천히 올리는 편이 좋습니다.",
        "호감 신호가 분명해도 결론을 급히 내리기보다 행동 일관성을 먼저 보는 편이 유리합니다.",
        "관계가 뜨거워질수록 대화 길이를 줄이고 핵심만 확인하는 방식이 오해를 줄입니다.",
    ],
    "balanced_connector": [
        "상대에게 맞추는 장점을 살리되 내 리듬을 지키는 기준을 같이 두는 편이 좋습니다.",
        "배려가 강점이라도 무리한 맞춤은 피하고 내가 편한 간격을 먼저 유지하는 편이 좋습니다.",
        "관계를 조율할 때 양쪽 요구를 다 받기보다 핵심 두 가지 기준만 지키는 편이 안정적입니다.",
        "상대 속도에 맞출수록 내 피로도도 함께 점검해 균형을 맞추는 편이 유리합니다.",
        "대화가 잘 풀려도 약속 범위를 작게 시작하면 장기적으로 더 안정적인 흐름이 됩니다.",
        "연결 능력을 살리되 선택과 집중을 분명히 하면 관계 소모를 크게 줄일 수 있습니다.",
    ],
}

RELATIONSHIP_STRENGTH_HEADLINE_CLAUSES = {
    "strong": [
        "감정이 커져도 기준을 지키는 힘이 있어 관계 운영이 비교적 안정적입니다.",
        "표현과 판단을 같이 끌고 가기 쉬운 버팀이 확보되는 편입니다.",
        "관계 압박이 와도 리듬을 유지하며 방향을 잡기 수월한 흐름입니다.",
        "중요한 대화를 실행으로 연결할 힘이 비교적 선명합니다.",
        "관계 속도 조절만 해도 만족도를 크게 높이기 쉬운 편입니다.",
    ],
    "slightly_strong": [
        "기본 버팀이 있어 관계 리듬을 안정적으로 맞추기 좋습니다.",
        "초반 기준만 분명히 하면 관계 운영이 한결 수월해질 수 있습니다.",
        "무리하지 않아도 중요한 장면에서 중심을 잡기 쉬운 흐름입니다.",
        "연락·만남 간격만 조정해도 피로를 줄이기 쉬운 편입니다.",
        "호감과 현실 조건을 병행해 보기에 비교적 유리합니다.",
    ],
    "balanced": [
        "감정과 현실의 균형을 맞출수록 관계 흐름이 안정됩니다.",
        "속도와 거리 조절을 함께 두면 갈등 가능성을 줄이기 쉽습니다.",
        "한쪽으로 몰아치지 않는 운영이 만족도를 높이기 좋습니다.",
        "중간 점검 대화를 넣으면 오해를 줄이는 데 도움이 됩니다.",
        "천천히 합의 범위를 맞출수록 관계 품질이 좋아질 수 있습니다.",
    ],
    "slightly_weak": [
        "관계 범위를 줄이고 핵심 약속만 남길수록 안정감이 커질 수 있습니다.",
        "표현 강도보다 회복 간격을 먼저 두는 편이 더 유리합니다.",
        "결론 속도를 늦추고 확인 과정을 늘리면 오차를 줄이기 쉽습니다.",
        "감정이 커질수록 기준을 짧게 적어 두는 방식이 도움이 됩니다.",
        "한 번에 깊어지기보다 단계적으로 맞춰 가는 편이 안정적입니다.",
    ],
    "weak": [
        "올해는 관계 확장보다 방어와 회복 운영이 먼저 맞는 흐름입니다.",
        "감정 소모를 줄이는 선택이 실제 만족도를 더 높일 수 있습니다.",
        "무리한 진전보다 현재 리듬을 지키는 편이 훨씬 안전합니다.",
        "관계 결론은 작게 쪼개고 확인 단계를 두는 방식이 유리합니다.",
        "연락·만남 빈도를 줄여 피로를 관리하는 편이 좋습니다.",
    ],
}

RELATIONSHIP_PATTERN_HEADLINE_CLAUSES = {
    "관성격": [
        "관계에서도 책임·신뢰·일관성 기준이 성패를 가를 수 있습니다.",
        "좋아도 기준과 역할을 먼저 맞출수록 안정성이 커질 수 있습니다.",
        "관계 압박 장면에서 원칙 유지가 큰 차이를 만들 수 있습니다.",
    ],
    "재성격": [
        "감정보다 현실 조건·유지 가능성 판단이 더 중요해질 수 있습니다.",
        "관계에서도 시간·에너지 배분 기준이 체감 결과를 좌우할 수 있습니다.",
        "좋아도 생활 리듬과 현실 조건을 같이 봐야 하는 흐름입니다.",
    ],
    "식상격": [
        "표현과 행동 일치가 관계 만족도를 크게 좌우할 수 있습니다.",
        "말보다 실제 행동과 약속 이행에서 차이가 벌어지기 쉽습니다.",
        "감정 표현의 순서를 다듬을수록 오해를 줄이기 유리합니다.",
    ],
    "인성격": [
        "관찰·확인·맥락 읽기가 관계 판단의 핵심이 되기 쉽습니다.",
        "성급한 결론보다 근거를 쌓는 대화가 더 유리할 수 있습니다.",
        "상대 의도와 분위기를 재확인하는 습관이 안정에 도움이 됩니다.",
    ],
    "비겁격": [
        "가까운 관계에서도 경계·거리·주도권 조율이 중요해집니다.",
        "관계 에너지 분산을 줄이는 기준이 만족도를 좌우할 수 있습니다.",
        "서로의 영역을 분명히 할수록 갈등 피로를 줄이기 쉽습니다.",
    ],
    "균형격": [
        "한쪽으로 치우치지 않는 관계 운영이 가장 큰 강점으로 작동합니다.",
        "속도보다 일관성 유지가 관계 안정으로 이어지기 쉬운 흐름입니다.",
        "작은 조정을 반복하는 방식이 관계 품질을 지키는 데 유리합니다.",
    ],
}

RELATIONSHIP_STAR_HEADLINE_CLAUSES = {
    "비견": ["관계에서 내 기준과 주도권 의식이 강해질 수 있습니다.", "내 판단 중심으로 관계 속도를 정하려는 흐름이 커질 수 있습니다."],
    "겁재": ["관계·사람 이슈가 늘어 감정 분산 관리가 중요해질 수 있습니다.", "주변 변수로 관계 리듬이 흔들리기 쉬워 조율이 필요합니다."],
    "식신": ["표현과 행동이 맞아떨어질수록 관계 만족도가 올라가기 쉽습니다.", "작은 배려 행동이 관계 흐름을 안정시킬 수 있습니다."],
    "상관": ["표현 강도가 커질 수 있어 말의 수위 조절이 중요합니다.", "맞는 말이라도 타이밍과 순서 관리가 필요해지는 흐름입니다."],
    "편재": ["새 접점이 늘어도 선별과 거리 조절이 핵심이 될 수 있습니다.", "호감 신호가 늘수록 속도 조절이 더 중요해집니다."],
    "정재": ["안정 지향적 관계 운영이 유리하게 작동할 수 있습니다.", "생활 리듬이 맞는 관계에서 편안함이 커지기 쉽습니다."],
    "편관": ["긴장과 압박 반응이 올라오기 쉬워 결론을 늦추는 편이 좋습니다.", "관계 판단에서 방어 기준을 먼저 두는 흐름이 커질 수 있습니다."],
    "정관": ["신뢰와 책임 기준이 선명해져 관계 방향이 또렷해질 수 있습니다.", "관계 정의와 기준 합의가 중요한 시기가 될 수 있습니다."],
    "편인": ["관계에서 생각이 길어지고 탐색 성향이 강해질 수 있습니다.", "확정 전 비교·관찰이 길어지는 흐름이 올라올 수 있습니다."],
    "정인": ["배려와 이해의 완충 역할이 관계 안정에 도움이 될 수 있습니다.", "천천히 맞춰 가는 운영이 더 큰 만족으로 이어질 수 있습니다."],
}

RELATIONSHIP_HEADLINE_TEMPLATES = [
    "{core} {pattern}",
    "{core} {strength}",
    "{core} {star}",
    "{pattern} {strength}",
    "{pattern} {star}",
    "{strength} {star}",
    "{core} {pattern} {star}",
    "{core} {strength} {star}",
    "{pattern} {strength} {star}",
    "{core} {pattern} {strength}",
]

RELATIONSHIP_SUMMARY_TEMPLATES = [
    "{profile} {flow}",
    "{profile} {trend}",
    "{profile} {strength}",
    "{flow} {star}",
    "{trend} {star}",
    "{strength} {pattern}",
    "{profile} {flow} {trend}",
    "{profile} {strength} {star}",
    "{flow} {pattern} {trend}",
    "{profile} {pattern} {flow}",
]

RELATIONSHIP_HEADLINE_COOLDOWN_WINDOW = 2
_RELATIONSHIP_RECENT_INDEXES: dict[str, deque[int]] = defaultdict(
    lambda: deque(maxlen=RELATIONSHIP_HEADLINE_COOLDOWN_WINDOW)
)
_RELATIONSHIP_HEADLINE_LOCK = Lock()


def _seed_from_values(*parts: object) -> int:
    total = 0
    for part in parts:
        if part is None:
            continue
        text = str(part)
        total += sum(ord(char) for char in text)
    return total


def _pick_seeded(options: list[str], seed: int) -> str:
    return options[seed % len(options)]


def _relationship_strength_key(analysis_context: dict | None) -> str:
    if not analysis_context:
        return "balanced"
    label = analysis_context.get("strength", {}).get("label", "balanced")
    return label if label in RELATIONSHIP_STRENGTH_HEADLINE_CLAUSES else "balanced"


def _build_relationship_headline_candidates(
    *,
    saju_id: str,
    relationship_profile: str,
    flow_profile: str,
    intensity: str,
    day_pillar_kor: str,
    current_stars: list[str],
    analysis_context: dict | None,
) -> list[str]:
    base_seed = _seed_from_values(
        saju_id,
        relationship_profile,
        flow_profile,
        intensity,
        day_pillar_kor,
        current_stars[0] if current_stars else "",
        current_stars[1] if len(current_stars) > 1 else "",
        analysis_context.get("structure", {}).get("primary_pattern", "") if analysis_context else "",
        analysis_context.get("strength", {}).get("label", "") if analysis_context else "",
    )
    core_base = _build_profile_headline(relationship_profile, flow_profile, intensity, day_pillar_kor)
    profile_sentence = RELATIONSHIP_PROFILE_HEADLINES[relationship_profile]
    flow_sentence = _build_headline(flow_profile, intensity)
    core_options = [
        core_base,
        profile_sentence,
        flow_sentence,
        f"{profile_sentence.rstrip('.')} 흐름이 올해 관계 판단의 핵심으로 작동할 가능성이 큽니다.",
    ]
    pattern_key = (
        analysis_context.get("structure", {}).get("primary_pattern", "균형격")
        if analysis_context
        else "균형격"
    )
    pattern_options = RELATIONSHIP_PATTERN_HEADLINE_CLAUSES.get(
        pattern_key,
        RELATIONSHIP_PATTERN_HEADLINE_CLAUSES["균형격"],
    )
    strength_options = RELATIONSHIP_STRENGTH_HEADLINE_CLAUSES[_relationship_strength_key(analysis_context)]
    star_options = RELATIONSHIP_STAR_HEADLINE_CLAUSES.get(
        current_stars[0] if current_stars else "",
        RELATIONSHIP_STAR_HEADLINE_CLAUSES["정인"],
    )
    if len(current_stars) > 1 and current_stars[1] in RELATIONSHIP_STAR_HEADLINE_CLAUSES:
        star_options = [*star_options, *RELATIONSHIP_STAR_HEADLINE_CLAUSES[current_stars[1]]]

    candidates: list[str] = []
    seen = set()
    for idx, template in enumerate(RELATIONSHIP_HEADLINE_TEMPLATES):
        sentence = template.format(
            core=_pick_seeded(core_options, base_seed + idx * 3 + 1).rstrip("."),
            pattern=_pick_seeded(pattern_options, base_seed + idx * 5 + 2).rstrip("."),
            strength=_pick_seeded(strength_options, base_seed + idx * 7 + 3).rstrip("."),
            star=_pick_seeded(star_options, base_seed + idx * 11 + 4).rstrip("."),
        )
        sentence = " ".join(sentence.split()).strip()
        if not sentence.endswith("."):
            sentence += "."
        if sentence not in seen:
            seen.add(sentence)
            candidates.append(sentence)
    return candidates or [core_base]


def _pick_relationship_headline(
    *,
    saju_id: str,
    relationship_profile: str,
    flow_profile: str,
    intensity: str,
    day_pillar_kor: str,
    current_stars: list[str],
    analysis_context: dict | None,
) -> str:
    options = _build_relationship_headline_candidates(
        saju_id=saju_id,
        relationship_profile=relationship_profile,
        flow_profile=flow_profile,
        intensity=intensity,
        day_pillar_kor=day_pillar_kor,
        current_stars=current_stars,
        analysis_context=analysis_context,
    )
    seed = _seed_from_values(saju_id, relationship_profile, flow_profile, intensity, *current_stars)
    base_index = seed % len(options)
    pattern_key = (
        analysis_context.get("structure", {}).get("primary_pattern", "균형격")
        if analysis_context
        else "균형격"
    )
    strength_key = _relationship_strength_key(analysis_context)
    cooldown_key = (
        f"{saju_id}:{relationship_profile}:{flow_profile}:{intensity}:{'-'.join(current_stars)}:"
        f"{pattern_key}:{strength_key}"
    )
    with _RELATIONSHIP_HEADLINE_LOCK:
        recent = _RELATIONSHIP_RECENT_INDEXES[cooldown_key]
        selected_index = base_index
        if base_index in recent:
            for step in range(1, len(options)):
                candidate = (base_index + step) % len(options)
                if candidate not in recent:
                    selected_index = candidate
                    break
        recent.append(selected_index)
    return options[selected_index]


def _build_relationship_summary(
    *,
    saju_id: str,
    relationship_profile: str,
    flow_profile: str,
    intensity: str,
    trend: str,
    current_stars: list[str],
    analysis_context: dict | None,
) -> str:
    seed = _seed_from_values(
        "relationship_summary",
        saju_id,
        relationship_profile,
        flow_profile,
        intensity,
        trend,
        *current_stars,
        analysis_context.get("structure", {}).get("primary_pattern", "") if analysis_context else "",
        analysis_context.get("strength", {}).get("label", "") if analysis_context else "",
    )
    profile_clause = RELATIONSHIP_PROFILE_SUMMARIES[relationship_profile].rstrip(".")
    flow_clause = RELATIONSHIP_RULES[flow_profile][intensity].rstrip(".")
    trend_clause = f"관계 흐름은 {trend} 축에서 실제 체감 차이가 크게 벌어질 수 있습니다"
    star_clause = (
        f"연운 {current_stars[0]}와 대운 {current_stars[1]}이 겹쳐 관계 속도 조절의 중요도가 올라갈 수 있습니다"
        if len(current_stars) >= 2
        else f"연운 {current_stars[0]} 흐름이 들어와 관계 운영 기준이 중요해질 수 있습니다"
    )
    if analysis_context:
        strength_clause = (
            f"중간 계산 기준으로는 {analysis_context['strength']['display_label']} 구조라 "
            "연락 간격과 관계 범위를 먼저 정해 두는 편이 유리합니다"
        )
        pattern_clause = (
            f"핵심 구조가 {analysis_context['structure']['primary_pattern']}로 읽혀 "
            "감정과 현실 조건을 함께 맞추는 운영이 중요해질 수 있습니다"
        )
    else:
        strength_clause = "서두른 확정보다 관계 리듬을 천천히 맞추는 편이 더 안정적입니다"
        pattern_clause = "결론보다 합의 순서를 먼저 맞추는 운영이 도움이 됩니다"

    template = RELATIONSHIP_SUMMARY_TEMPLATES[seed % len(RELATIONSHIP_SUMMARY_TEMPLATES)]
    summary = template.format(
        profile=profile_clause,
        flow=flow_clause,
        trend=trend_clause,
        strength=strength_clause,
        star=star_clause,
        pattern=pattern_clause,
    )
    return f"{' '.join(summary.split()).strip().rstrip('.')}."


def build_relationship_fortune(
    gender: str,
    year_fortune: dict,
    saju_result: dict | None = None,
    analysis_context: dict | None = None,
) -> dict:
    """Build a relationship fortune from natal chart, gender, and yearly flow."""
    current_stars = [year_fortune["ten_god"], year_fortune["daewoon_ten_god"]]
    saju_id = str((saju_result or {}).get("saju_id", ""))
    current_star_set = set(current_stars)

    if gender == "male":
        relevant_stars = {"편재", "정재"}
        profile = "wealth"
    elif gender == "female":
        relevant_stars = {"편관", "정관"}
        profile = "officer"
    else:
        relevant_stars = {"편재", "정재", "편관", "정관"}
        profile = "mixed"

    strength_profile = profile if current_star_set & relevant_stars else "mixed"
    intensity = _resolve_intensity(current_stars, strength_profile)
    rule = RELATIONSHIP_RULES[strength_profile]
    strengths = list(rule["strengths"])
    warnings = list(rule["warnings"])
    relationship_profile = "balanced_connector"
    advanced_lines = _analysis_context_relationship_lines(analysis_context)

    context_easy_lines: list[str] = []
    context_real_lines: list[str] = []
    context_action_lines: list[str] = []

    if saju_result:
        saju = saju_result["saju"]
        day_stem = saju["day"]["stem"]
        day_pillar_kor = saju["day"]["kor"]
        month_branch = saju["month"]["branch"]
        time_branch = saju["time"]["branch"] if saju.get("time") else None
        ten_gods = calculate_ten_gods(saju)
        month_ten_god = ten_gods["ten_gods"]["month"]
        sentence_data = load_analysis_sentences()
        day_data = sentence_data["day_stem"][day_stem]
        month_data = sentence_data["month_branch"][month_branch]
        time_data = sentence_data["time_branch"].get(time_branch) if time_branch else None
        month_ten_god_data = sentence_data["month_ten_god"].get(month_ten_god) if month_ten_god else None
        seed = len("".join(current_stars)) + len(strength_profile) + len(day_stem) + len(month_branch)
        relationship_profile = _resolve_relationship_profile(day_stem, month_branch, time_branch)
        day_pillar_line = _pick(get_day_pillar_sentence_options(day_pillar_kor, "relationship"), seed)
        stripped_day_pillar_line = _strip_relationship_day_pillar_line(day_pillar_line).rstrip(".")
        month_ten_god_relation_line = (
            _pick(MONTH_TEN_GOD_RELATION_LINES[month_ten_god], seed + 2)
            if month_ten_god
            else ""
        )

        context_easy_lines = [
            f"연락을 이어 갈지, 거리를 둘지 정해야 하는 장면에서는 {stripped_day_pillar_line}",
            *advanced_lines["easy"],
            _normalize_relationship_support_line(month_ten_god_relation_line) if month_ten_god_relation_line else "",
            RELATIONSHIP_PROFILE_HEADLINES[relationship_profile],
            DAY_STEM_RELATION_LINES[day_stem],
            MONTH_BRANCH_RELATION_LINES[month_branch],
            _pick(day_data["social_reaction"], seed + 3),
        ]
        context_easy_lines = [line for line in context_easy_lines if line]
        if month_ten_god_data:
            context_easy_lines.append(
                _normalize_relationship_support_line(
                    _pick(month_ten_god_data["personality_modifier"], seed + 5).lower()
                )
            )
        if time_branch:
            context_easy_lines.append(TIME_BRANCH_RELATION_LINES[time_branch])

        context_real_lines = [
            f"연락 간격을 줄일지, 관계 정의를 서둘지 고민하는 장면에서는 {stripped_day_pillar_line}",
            *advanced_lines["real"],
            _pick(day_data["speech_style"], seed + 7),
            _pick(month_data["base_personality"], seed + 11),
            _pick(month_data["work_adaptation"], seed + 13),
        ]
        if time_data:
            context_real_lines.append(_pick(time_data["intimate_reaction"], seed + 17))

        context_action_lines = [
            "올해는 감정이 올라와도 관계 속도를 먼저 정하는 편이 흐름을 덜 흔듭니다.",
            "가까워질수록 생활 리듬과 연락 간격이 맞는지부터 보는 편이 좋습니다.",
            *advanced_lines["action"],
        ]

        strengths.extend(
            _dedupe(
                [
                    _pick(month_data["base_personality"], seed + 19),
                    _pick(day_data["social_reaction"], seed + 23),
                ]
            )[:2]
        )
        if time_branch and time_branch in RELATIONSHIP_SPEED_WARNINGS:
            warnings.append(RELATIONSHIP_SPEED_WARNINGS[time_branch])

    strengths.extend(advanced_lines["strengths"])
    warnings.extend(advanced_lines["warnings"])
    if "겁재" in current_star_set or "상관" in current_star_set:
        warnings.append("관계에서는 말의 강약이 강해질 수 있어 서두른 확정은 피하는 편이 좋습니다.")
    if "정인" in current_star_set or "편인" in current_star_set:
        strengths.append("상대를 천천히 이해하려는 태도가 관계 안정에 도움이 됩니다.")
    day_pillar_kor = saju_result["saju"]["day"]["kor"] if saju_result else ""
    day_pillar_line = (
        _pick(get_day_pillar_sentence_options(day_pillar_kor, "relationship"), len("".join(current_stars)) + len(strength_profile))
        if saju_result
        else ""
    )
    summary = _build_relationship_summary(
        saju_id=saju_id,
        relationship_profile=relationship_profile,
        flow_profile=strength_profile,
        intensity=intensity,
        trend=rule["trend"],
        current_stars=current_stars,
        analysis_context=analysis_context,
    )
    explanation = f"{_build_explanation(strength_profile, current_stars)} {RELATIONSHIP_PROFILE_SUMMARIES[relationship_profile]}".strip()
    profile_advice_lines = _dedupe(
        [
            _pick(RELATIONSHIP_PROFILE_ADVICE[relationship_profile], seed + 31),
            _pick(RELATIONSHIP_PROFILE_ADVICE[relationship_profile], seed + 37),
        ]
    )[:2]
    relationship_action_lines = _dedupe(
        [
            _pick(RELATIONSHIP_ACTION, seed + 43),
            _pick(RELATIONSHIP_ACTION, seed + 47),
        ]
    )[:2]
    base_advice = _build_advice(strength_profile, current_star_set)
    advice = f"{base_advice} {profile_advice_lines[0]}".strip() if profile_advice_lines else base_advice
    headline = _pick_relationship_headline(
        saju_id=saju_id,
        relationship_profile=relationship_profile,
        flow_profile=strength_profile,
        intensity=intensity,
        day_pillar_kor=day_pillar_kor or "이 원국",
        current_stars=current_stars,
        analysis_context=analysis_context,
    )
    limited_strengths = _dedupe(strengths)[:2]
    limited_warnings = _dedupe(warnings)[:2]
    section = build_relationship_section(
        headline=headline,
        explanation=explanation,
        advice=advice,
        strengths=limited_strengths,
        warnings=limited_warnings,
        seed=len("".join(current_stars)) + len(strength_profile),
        context_easy_lines=context_easy_lines,
        context_real_lines=context_real_lines,
        context_action_lines=context_action_lines,
    )
    section["easy_explanation"] = [_normalize_relationship_support_line(line) for line in section["easy_explanation"]]
    section["explanation"] = " ".join(section["easy_explanation"])
    section["strength_and_risk"] = _dedupe([*limited_strengths, *limited_warnings])[:4]
    section["strength_risk_text"] = " ".join(section["strength_and_risk"])
    # 행동조언 출력 고정:
    # - RELATIONSHIP_PROFILE_ADVICE: 최대 2개
    # - RELATIONSHIP_ACTION: 최대 2개
    # - 총합: 정확히 4개(중복 제거 후 부족분 보충)
    action_advice = _dedupe([*profile_advice_lines[:2], *relationship_action_lines[:2]])[:4]
    if not action_advice:
        action_advice = [base_advice]
    filler_candidates = _dedupe(
        [
            base_advice,
            *RELATIONSHIP_PROFILE_ADVICE[relationship_profile],
            *[_pick(RELATIONSHIP_ACTION, seed + 59 + idx * 5) for idx in range(20)],
        ]
    )
    for line in filler_candidates:
        if len(action_advice) >= 4:
            break
        if line and line not in action_advice:
            action_advice.append(line)
    action_advice = action_advice[:4]
    section["action_advice"] = action_advice
    section["advice"] = " ".join(action_advice)

    return {
        "headline": section["one_line"],
        "summary": summary,
        "explanation": " ".join(section["easy_explanation"]),
        "advice": " ".join(section["action_advice"]),
        "section": section,
        "trend": rule["trend"],
        "intensity": intensity,
        "intensity_kor": {"strong": "강", "medium": "보통", "light": "완만"}[intensity],
        "strengths": limited_strengths,
        "warnings": limited_warnings,
    }


def _resolve_intensity(stars: list[str], profile: str) -> str:
    if profile != "mixed" and stars[0] == stars[1]:
        return "strong"
    if any(star in {"겁재", "상관", "편재", "편관"} for star in stars):
        return "medium"
    return "light"


def _build_headline(profile: str, intensity: str) -> str:
    headline_map = {
        ("wealth", "strong"): "인연 유입은 강하지만 관계 속도 조절이 더 중요합니다.",
        ("wealth", "medium"): "새로운 만남 가능성은 있지만 서두르지 않는 편이 좋습니다.",
        ("wealth", "light"): "가벼운 접점을 넓히며 흐름을 지켜보기 좋은 시기입니다.",
        ("officer", "strong"): "관계 판단이 또렷해져 기준을 분명히 해야 하는 시기입니다.",
        ("officer", "medium"): "인연보다 관계의 안정성과 책임감을 먼저 볼 시기입니다.",
        ("officer", "light"): "천천히 관계 기준을 맞춰 가기 좋은 흐름입니다.",
        ("mixed", "strong"): "관계는 유지보다 재정비 흐름이 더 강하게 들어옵니다.",
        ("mixed", "medium"): "관계 속도보다 대화 방식 조정이 먼저입니다.",
        ("mixed", "light"): "감정의 결론을 서두르지 않으면 흐름이 부드럽습니다.",
    }
    return headline_map[(profile, intensity)]


def _build_profile_headline(relationship_profile: str, flow_profile: str, intensity: str, day_pillar_kor: str) -> str:
    flow_suffix = {
        ("wealth", "strong"): "지금은 만남이 들어와도 속도 조절이 더 중요합니다.",
        ("wealth", "medium"): "지금은 접점은 열리지만 서두르지 않는 편이 좋습니다.",
        ("wealth", "light"): "지금은 가벼운 접점을 넓히며 지켜보기 좋은 시기입니다.",
        ("officer", "strong"): "지금은 관계 기준을 분명히 해야 흐름이 살아납니다.",
        ("officer", "medium"): "지금은 안정성과 책임감을 먼저 보는 편이 맞습니다.",
        ("officer", "light"): "지금은 천천히 기준을 맞춰 가기 좋은 흐름입니다.",
        ("mixed", "strong"): "지금은 유지보다 재정비가 먼저인 시기입니다.",
        ("mixed", "medium"): "지금은 관계 속도보다 대화 방식 조정이 먼저입니다.",
        ("mixed", "light"): "지금은 결론을 서두르지 않으면 더 편안한 흐름입니다.",
    }[(flow_profile, intensity)]
    headline_body = RELATIONSHIP_PROFILE_HEADLINES[relationship_profile].replace("관계는 ", "").rstrip(".")
    return (
        f"가까워질지 거리를 둘지 정해야 하는 장면에서는 {day_pillar_kor} 일주의 결이 먼저 올라와 {headline_body}. "
        f"{flow_suffix}"
    )


def _build_explanation(profile: str, stars: list[str]) -> str:
    profile_phrase = {
        "wealth": "사람과 감정 흐름이 들어와도 가까워지는 속도와 현실 조건을 같이 봐야 하는 장면이 늘어날 수 있습니다.",
        "officer": "호감보다 관계의 기준과 책임감이 먼저 보이는 장면이 늘어날 수 있습니다.",
        "mixed": "새 인연을 넓히기보다 지금 있는 관계의 속도와 대화 방식을 다시 맞춰야 하는 일이 더 많아질 수 있습니다.",
    }[profile]
    return f"올해는 {profile_phrase}"


def _build_advice(profile: str, star_set: set[str]) -> str:
    if "겁재" in star_set or "상관" in star_set:
        return "호감이 생겨도 속도를 늦추고 말의 강약을 조절하는 편이 좋습니다."
    if profile == "wealth":
        return "인연이 보여도 감정만 보지 말고 생활 리듬과 현실 조건을 같이 보는 편이 좋습니다."
    if profile == "officer":
        return "상대 기준보다 내 기준을 먼저 분명히 해야 관계가 안정됩니다."
    return "관계를 바로 정의하기보다 대화 방식과 거리 조절부터 정리하는 편이 좋습니다."


def _pick(options: list[str], seed: int) -> str:
    return options[seed % len(options)]


def _resolve_relationship_profile(day_stem: str, month_branch: str, time_branch: str | None) -> str:
    if time_branch in {"축", "미", "술"} or month_branch in {"축", "미"}:
        return "slow_trust"
    if time_branch in {"사", "오"} or day_stem in {"병", "정"}:
        return "expressive"
    if time_branch in {"신", "유"} or day_stem in {"경", "신"}:
        return "boundary_first"
    if time_branch in {"자", "해"} or day_stem in {"임", "계"}:
        return "observer"
    if month_branch in {"묘", "진"} or day_stem in {"을", "기"}:
        return "balanced_connector"
    return "pace_adjuster"


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _analysis_context_relationship_lines(analysis_context: dict | None) -> dict[str, list[str]]:
    if not analysis_context:
        return {"easy": [], "real": [], "action": [], "strengths": [], "warnings": []}

    strength = analysis_context["strength"]
    yongshin = analysis_context["yongshin"]
    flags = analysis_context["flags"]
    interactions = analysis_context["interactions"]
    hidden_focus = flags.get("hidden_group_focus")

    easy_lines = [
        _relationship_strength_scene_line(strength),
        _relationship_yongshin_scene_line(yongshin),
    ]
    hidden_focus_line = _relationship_hidden_focus_line(hidden_focus)
    if hidden_focus_line:
        easy_lines.append(hidden_focus_line)

    real_lines: list[str] = []
    if interactions["natal"]:
        item = interactions["natal"][0]
        real_lines.append(f"좋아도 바로 다가갈지, 한발 물러설지 고민하는 장면에서는 {item['meaning']}")
    if interactions["with_yearly"]:
        item = interactions["with_yearly"][0]
        real_lines.append(f"올해는 연락 빈도와 관계 속도를 맞추는 과정에서 {item['meaning']}")

    action_lines: list[str] = []
    action_lines.append(_relationship_action_support_line(flags, yongshin))

    strengths: list[str] = []
    warnings: list[str] = []
    if flags["is_day_master_strong"]:
        strengths.append("원국 기준으로는 쉽게 흔들리지 않는 편이라 관계 속도가 달라도 기준을 지키는 힘이 남아 있는 편입니다.")
    if flags["is_day_master_weak"]:
        warnings.append("원국 기준으로는 감정 소모가 빨리 올라올 수 있어 관계 진전보다 회복 간격을 먼저 챙기는 편이 좋습니다.")
    if flags["has_luck_pressure"]:
        warnings.append("현재 운에서 충돌 압력이 걸릴 수 있어 감정이 커져도 확정은 한 박자 늦추는 편이 좋습니다.")

    return {
        "easy": easy_lines,
        "real": real_lines,
        "action": action_lines,
        "strengths": strengths,
        "warnings": warnings,
    }
