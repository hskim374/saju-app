"""Career fortune interpretation from natal chart and current flows."""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock

from data.day_pillar_sentences import get_day_pillar_sentence_options
from data.month_ten_god_specialized import MONTH_TEN_GOD_CAREER_LINES
from services.analysis_sentence_store import load_analysis_sentences
from services.interpretation_engine import build_career_section
from services.ten_gods import calculate_ten_gods

ELEMENT_KOR_ONLY = {
    "wood": "목",
    "fire": "화",
    "earth": "토",
    "metal": "금",
    "water": "수",
}


def _career_strength_scene_line(strength: dict) -> str:
    label = strength["label"]
    if label in {"weak", "slightly_weak"}:
        return "직장에서는 한 번에 많은 일을 떠안기보다, 버틸 범위와 마감 간격을 먼저 정하는 편이 더 안정적입니다."
    if label in {"strong", "slightly_strong"}:
        return "직장에서는 힘이 한쪽으로 몰리기 쉬워, 처음부터 너무 세게 밀기보다 중간 점검을 넣는 편이 흐름을 지키기 쉽습니다."
    return "직장에서는 해야 할 일을 몇 덩어리로 나눠 움직이는 편이 전체 리듬을 지키는 데 도움이 됩니다."


def _career_yongshin_scene_line(yongshin: dict) -> str:
    primary_map = {
        "wood": "막힌 일을 조금 열어 두고 새 방향 하나를 남기는",
        "fire": "필요한 말과 존재감을 분명히 드러내는",
        "earth": "버틸 범위와 현실 조건을 먼저 잡는",
        "metal": "기준과 순서를 먼저 분명히 하는",
        "water": "바로 확정하지 않고 흐름을 한 번 더 살피는",
    }
    secondary_map = {
        "wood": "다음 선택지의 여지를 남기는",
        "fire": "전달 강도를 한 번 더 다듬는",
        "earth": "무리 없는 범위를 다시 확인하는",
        "metal": "세부 기준을 차분히 정리하는",
        "water": "결론을 서두르지 않는",
    }
    primary_phrase = primary_map.get(yongshin["primary_candidate"], "먼저 기준을 세우는")
    secondary_phrase = secondary_map.get(yongshin["secondary_candidate"], "한 번 더 살펴보는")
    return f"직장에서는 {primary_phrase} 쪽으로 움직이고, {secondary_phrase} 정도의 여지도 같이 챙기는 편이 좋습니다."


def _career_hidden_focus_line(group: str | None) -> str:
    mapping = {
        "비겁": "직장에서는 내 역할과 남의 역할 경계가 예민해져, 맡을 일과 넘길 일을 빨리 나눌수록 피로를 줄이기 쉽습니다.",
        "식상": "직장에서는 말보다 결과와 마감 순서를 어떻게 잡느냐가 실력 차이로 이어지기 쉽습니다.",
        "재성": "직장에서는 성과와 효율을 먼저 따지는 반응이 올라와, 시간 대비 남는 일을 고르는 편이 좋습니다.",
        "관성": "직장에서는 책임 범위와 평가 기준을 먼저 보게 돼, 역할 선을 분명히 할수록 흔들림이 줄어듭니다.",
        "인성": "직장에서는 서두르기보다 자료와 맥락을 다시 확인하고 싶은 마음이 강해져, 보고 전에 한 번 더 정리하면 좋습니다.",
    }
    return mapping.get(group or "", "")


def _career_action_support_line(flags: dict, yongshin: dict) -> str:
    primary_map = {
        "wood": "막힌 일 하나를 먼저 열어 두는",
        "fire": "필요한 말과 존재감을 분명히 보이는",
        "earth": "버틸 범위와 현실 조건을 먼저 잡는",
        "metal": "기준과 순서를 먼저 정리하는",
        "water": "바로 확정하지 않고 한 번 더 살피는",
    }
    primary_phrase = primary_map.get(yongshin["primary_candidate"], "먼저 기준을 세우는")
    if flags["needs_resource_support"]:
        return "일은 바로 넓히기보다 준비와 기준을 먼저 채우는 쪽이 더 잘 맞습니다."
    if flags["needs_output_release"]:
        return "일은 오래 끌기보다 보이게 끝낸 결과 하나를 먼저 만드는 편이 좋습니다."
    return f"일은 한쪽으로 몰아치기보다 {primary_phrase} 방식으로 운영하는 편이 더 안정적입니다."


def _normalize_career_support_line(line: str) -> str:
    normalized = line.strip()
    for prefix in ("그래서, ", "결국, ", "여기서 중요한 건, ", "다만, ", "특히, ", "대신, "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    replacements = (
        ("실무적으로 풀면 ", ""),
        ("직업 흐름 보정으로는 ", ""),
        ("실무 방향으로 읽으면 ", ""),
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
    )
    for source, target in replacements:
        if normalized.startswith(source):
            normalized = target + normalized[len(source):]
            break
    return normalized


def _strip_career_day_pillar_line(line: str) -> str:
    normalized = line.strip()
    prefixes = (
        "일이 한꺼번에 몰릴 때는 ",
        "역할을 나눠야 하는 장면에서는 ",
        "결정을 바로 내려야 하는 순간에는 ",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return normalized

POSITIVE_STARS = {"정관", "정인", "식신", "정재"}
CHANGE_STARS = {"편관", "편인", "상관", "편재"}
CAUTION_STARS = {"겁재", "상관", "편관"}

CAREER_STRENGTHS = {
    "정관": "조직 안에서 역할이 또렷해지고 책임이 커질 수 있는 흐름입니다.",
    "편관": "압박이 강하지만 버티면 자리 변동이나 역할 확장이 연결될 수 있습니다.",
    "정인": "자격, 학습, 지원 체계를 붙이면 직장운이 안정적으로 받쳐집니다.",
    "편인": "새 방식이나 다른 직무 감각을 익히면 전환 기회를 만들 수 있습니다.",
    "식신": "실무 성과를 꾸준히 쌓아 신뢰를 얻기 좋은 흐름입니다.",
    "상관": "표현력과 문제 제기가 성과로 이어질 수 있지만 강약 조절이 필요합니다.",
    "정재": "관리 능력과 실적을 함께 보여주기 좋은 흐름입니다.",
    "편재": "외부 기회나 자리 이동 가능성이 열릴 수 있는 흐름입니다.",
    "비견": "내 역할을 직접 잡고 주도권을 만드는 데 힘이 실립니다.",
    "겁재": "경쟁이 강해져도 존재감을 드러낼 수 있으나 무리한 승부는 피해야 합니다.",
}

CAREER_WARNINGS = {
    "상관": [
        "평가가 걸린 자리에서는 말의 수위와 문서 표현을 한 번 더 다듬는 편이 좋습니다.",
        "문제 제기가 빠를수록 표현 강도도 올라가기 쉬워 순서를 맞춘 전달이 필요합니다.",
        "맞는 말이라도 타이밍이 어긋나면 마찰이 커질 수 있어 결론 시점을 분리하는 편이 안전합니다.",
        "보고·피드백 장면에서는 핵심 메시지를 줄여 전달해야 오해를 줄일 수 있습니다.",
        "직설적 표현이 장점으로 작동하되, 평가 구간에서는 완충 문장을 먼저 두는 편이 유리합니다.",
    ],
    "겁재": [
        "올해는 경쟁이 강해져 자리 변동 가능성이 있어 충동적인 이직 판단은 늦추는 편이 안전합니다.",
        "동시에 여러 일을 잡기 쉬운 흐름이라 우선순위가 없으면 성과가 분산될 수 있습니다.",
        "사람 이슈가 겹치면 에너지가 빠르게 소모될 수 있어 협업 범위를 좁혀 운영해야 합니다.",
        "주도권을 모두 직접 쥐려 하면 피로가 커져 선택과 위임을 함께 쓰는 편이 좋습니다.",
        "경쟁 구간일수록 빠른 결론보다 손실 한도를 먼저 정해 움직이는 편이 안전합니다.",
    ],
    "편관": [
        "압박이 커질수록 체력과 감정 소모가 누적될 수 있어 일정 간격으로 리듬을 비워야 합니다.",
        "책임이 갑자기 늘어날 수 있는 흐름이라 역할 상한선을 숫자로 정해 두는 편이 좋습니다.",
        "평가와 마감이 겹치면 과부하가 오기 쉬워 핵심 과제만 남기는 운영이 필요합니다.",
        "도전 과제를 맡더라도 중간 점검을 빼면 리스크가 커질 수 있어 확인 절차를 고정해야 합니다.",
        "압력이 강한 시기에는 실수 한 번이 크게 체감될 수 있어 속도보다 정확도를 우선해야 합니다.",
    ],
    "편재": [
        "기회가 많아 보일수록 우선순위를 정하지 않으면 성과가 흩어질 수 있습니다.",
        "외부 제안이 늘어도 조건표 없이 받으면 일정과 자원이 쉽게 꼬일 수 있습니다.",
        "수익 가능성이 보여도 유지 가능성을 먼저 보지 않으면 후반 부담이 커질 수 있습니다.",
        "단기 성과 중심 선택이 반복되면 경력 방향이 흔들릴 수 있어 기준 고정이 필요합니다.",
        "기회 선별 없이 확장하면 마무리 품질이 내려갈 수 있어 진입 기준을 엄격히 두는 편이 좋습니다.",
    ],
    "비견": [
        "자기 판단이 강해질수록 협업 신호를 분명히 해야 충돌을 줄일 수 있습니다.",
        "독자 추진력이 올라올수록 역할 경계가 흐려져 팀 마찰이 생길 수 있습니다.",
        "내 기준이 선명한 장점이 과해지면 조정 비용이 커질 수 있어 합의 절차를 먼저 맞춰야 합니다.",
        "혼자 해결하려는 성향이 강해질수록 일정 과부하가 오기 쉬워 지원 요청 시점을 정해 두는 편이 좋습니다.",
        "주도권을 잡는 흐름이 강할수록 협업 규칙을 명시해 불필요한 오해를 줄여야 합니다.",
    ],
}

MONTH_BRANCH_WATER_WARNING_VARIANTS = [
    "생각이 길어질수록 실행 시점이 밀릴 수 있어 마감 기준을 먼저 정하는 편이 좋습니다.",
    "검토가 길어지는 구간이라 결정 시간을 제한하지 않으면 일정이 뒤로 밀리기 쉽습니다.",
    "정보를 더 모으려는 성향이 강해져도 결론 마감선을 먼저 잡아야 리듬이 무너지지 않습니다.",
    "확인 단계가 길어지면 실행력이 떨어질 수 있어 초반에 완료 기준을 명확히 두는 편이 안전합니다.",
    "판단이 깊어지는 장점이 일정 지연으로 이어지지 않도록 중간 확정 지점을 나눠 두는 편이 좋습니다.",
]

MONTH_BRANCH_FIRE_WARNING_VARIANTS = [
    "속도가 붙는 시기일수록 말의 강약과 보고 타이밍을 조절해야 평판 손실을 줄일 수 있습니다.",
    "추진력이 커지는 구간이라 반응이 앞서기 쉬워 결론 전에 확인 단계를 한 번 더 두는 편이 좋습니다.",
    "빠른 실행이 장점이지만 보고 순서가 어긋나면 오해가 커질 수 있어 전달 구조를 먼저 정리해야 합니다.",
    "속도가 올라올수록 작은 실수가 커질 수 있어 핵심 일정은 재확인 루틴을 고정하는 편이 안전합니다.",
    "강하게 밀어붙이기 쉬운 흐름이라 합의 없는 확정은 줄이고 중간 공유를 늘리는 편이 유리합니다.",
]

TIME_BRANCH_METAL_WARNING_VARIANTS = [
    "완성도를 높이려는 마음이 과해지면 마감이 늦어질 수 있어 끝내는 기준을 먼저 세우는 편이 좋습니다.",
    "디테일 점검이 길어지는 흐름이라 수정 횟수 상한선을 두지 않으면 일정이 밀릴 수 있습니다.",
    "품질 의식이 강한 장점이 과도해지면 속도가 떨어질 수 있어 제출 시점을 먼저 고정하는 편이 좋습니다.",
    "정밀 검토가 필요한 시기일수록 우선순위 없는 보완은 피하고 핵심 항목만 남겨야 합니다.",
    "완성도 집착이 피로로 바뀌기 쉬워 마감선 이후 보완은 다음 주기로 넘기는 운영이 필요합니다.",
]

STAR_SHANGGUAN_WARNING_VARIANTS = [
    "문제 인식이 빨라질수록 표현도 세질 수 있어 맞는 말이라도 순서를 조절하는 편이 좋습니다.",
    "개선 포인트를 빠르게 짚을수록 상대 체감 압박이 커질 수 있어 전달 강도를 낮추는 편이 유리합니다.",
    "비판적 시각이 장점으로 작동하되 평가 자리에서는 제안형 문장으로 바꾸는 편이 안전합니다.",
    "직접적인 피드백은 오해를 부를 수 있어 근거-대안-결론 순서로 말하는 편이 좋습니다.",
    "표현력이 올라오는 구간일수록 결론보다 합의 가능한 조건부터 맞추는 편이 마찰을 줄입니다.",
]

WEAK_WARNING_VARIANTS = [
    "원국 기준으로는 소모가 빠를 수 있어 역할이 늘수록 체력과 일정 간격을 먼저 확보하는 편이 좋습니다.",
    "신약 흐름에서는 한 번에 많은 책임을 받으면 회복이 늦어질 수 있어 업무 상한선을 먼저 정해야 합니다.",
]

LUCK_PRESSURE_WARNING_VARIANTS = [
    "현재 운에서 충돌 압력이 걸릴 수 있어 자리 이동이나 확장은 기준을 더 엄격하게 보는 편이 좋습니다.",
    "운 압박 구간에서는 작은 변수도 크게 체감될 수 있어 결정 전 체크 항목을 고정하는 편이 안전합니다.",
]

CAREER_WARNING_FALLBACK = "큰 결정은 일정과 조건을 숫자로 정리한 뒤 판단하는 편이 좋습니다."

DAY_STEM_CAREER_LINES = {
    "갑": "프로젝트 방향을 잡아야 하는 장면에서는 먼저 큰 판과 역할 배치를 보는 쪽이 더 자연스럽습니다.",
    "을": "팀 안에서 의견이 갈릴 때는 정면 충돌보다 조정과 연결로 일을 풀어 가는 편입니다.",
    "병": "발표나 보고처럼 존재감이 필요한 장면에서는 반응 속도와 추진력이 강점으로 살아나기 쉽습니다.",
    "정": "회의 분위기가 미묘할수록 타이밍을 읽고 필요한 순간에 힘을 주는 방식이 더 잘 맞습니다.",
    "무": "업무 범위가 커질수록 버틸 수 있는 기준과 현실성을 먼저 확보해야 힘이 안정적으로 붙습니다.",
    "기": "여러 사람 일정과 조건을 함께 맞춰야 할 때 무리 없는 운영안을 만드는 쪽에서 강점이 살아납니다.",
    "경": "기준이 흐리거나 결론이 늦어지는 장면에서는 선을 긋고 방향을 정리하는 쪽으로 존재감이 커지기 쉽습니다.",
    "신": "검수, 문서, 마감처럼 디테일과 완성도를 챙겨야 하는 장면에서 평판이 올라가기 쉽습니다.",
    "임": "단기 성과보다 다음 수순까지 계산해야 하는 장면에서 판단의 강점이 더 선명하게 드러납니다.",
    "계": "겉으로 드러난 말보다 맥락을 읽고 조용히 방향을 조정해야 하는 장면에서 힘이 살아 있습니다.",
}

MONTH_BRANCH_CAREER_LINES = {
    "자": "정보가 한꺼번에 몰리는 날에는 먼저 흐름을 읽고 정리해야 움직임이 안정되는 편입니다.",
    "축": "역할이 흔들릴수록 속도보다 버틸 수 있는 시스템과 기본 틀을 세우는 쪽이 더 잘 맞습니다.",
    "인": "정체된 판보다 앞으로 확장되는 프로젝트나 새 역할이 보일 때 힘이 더 잘 붙을 수 있습니다.",
    "묘": "협업 상대가 많아질수록 관계 조율과 연결 감각이 필요한 장면에서 강점을 보이기 쉽습니다.",
    "진": "업무가 복잡하게 얽힐수록 여러 일을 현실적으로 묶어 정리하는 역할에서 신뢰를 얻기 쉽습니다.",
    "사": "반응 속도와 존재감이 필요한 자리에서는 강점이 선명하게 보일 가능성이 큽니다.",
    "오": "움직임이 보이고 주도성이 필요한 환경일수록 에너지가 잘 붙는 편입니다.",
    "미": "급한 성과보다 오래 갈 수 있는 운영 감각이 필요한 장면에서 차이를 만들기 쉽습니다.",
    "신": "마감, 검수, 정리, 우선순위 조정 같은 실무 결에서 강점이 두드러질 가능성이 큽니다.",
    "유": "작은 오류와 완성도를 챙겨야 하는 조직에서 신뢰를 얻기 쉬운 편입니다.",
    "술": "책임 범위와 역할 기준이 분명할수록 실력이 안정적으로 드러나는 편입니다.",
    "해": "바로 확정하기보다 전체 맥락과 여지를 보며 움직여야 하는 장면에서 더 자연스럽습니다.",
}

YEAR_STEM_IMPRESSION_LINES = {
    "갑": "년간이 갑이면 바깥에서는 주도권을 잡으려는 사람으로 읽히기 쉬워 첫인상이 또렷한 편입니다.",
    "을": "년간이 을이면 외부에서는 유연하게 조율하는 사람으로 보일 가능성이 큽니다.",
    "병": "년간이 병이면 공적인 자리에서 존재감과 표현력이 먼저 읽히기 쉬운 편입니다.",
    "정": "년간이 정이면 바깥에서는 섬세하고 눈치가 빠른 사람이라는 인상이 남기 쉽습니다.",
    "무": "년간이 무이면 공적인 자리에선 무게감 있고 쉽게 흔들리지 않는 인상으로 읽히기 쉽습니다.",
    "기": "년간이 기이면 외부에서는 실무형이고 현실적인 사람으로 보는 경우가 많습니다.",
    "경": "년간이 경이면 바깥에서는 결론이 분명하고 기준이 선명한 사람으로 읽히기 쉽습니다.",
    "신": "년간이 신이면 공적인 자리에서 정리와 완성도를 챙기는 사람으로 보일 가능성이 큽니다.",
    "임": "년간이 임이면 외부에서는 흐름을 넓게 읽는 사람이라는 인상이 먼저 들어오기 쉽습니다.",
    "계": "년간이 계이면 공적인 자리에서는 조용하지만 맥락을 잘 읽는 사람으로 평가받기 쉽습니다.",
}

TIME_BRANCH_CAREER_LINES = {
    "자": "사적인 시간에는 생각이 길어질 수 있어 직장 판단도 마감 시점을 미리 정해 두는 편이 도움이 됩니다.",
    "축": "혼자 정리하는 과정이 길어질 수 있어 업무도 끝내는 기준을 먼저 잡는 편이 좋습니다.",
    "인": "시간이 갈수록 더 넓은 판을 보고 싶어질 수 있어 직장에서도 역할 확장 욕구가 올라오기 쉽습니다.",
    "묘": "가까운 관계일수록 부드럽게 조율하려는 성향이 있어 조직 내 협업 완충 역할을 맡기 쉬운 편입니다.",
    "진": "속으로 여러 선택지를 오래 비교하는 편이라 직장에서도 큰 결정은 체크리스트 방식이 잘 맞습니다.",
    "사": "친한 사람 앞에서는 표현이 빨라지기 쉬워 조직 내에서도 말의 속도를 조절하면 장점이 더 잘 남습니다.",
    "오": "마음이 움직였을 때 에너지가 크게 붙어 직장에서도 몰입할 때 성과 폭이 커지기 쉽습니다.",
    "미": "나중으로 갈수록 안정성을 더 보게 되어 직장에서도 오래 갈 구조를 찾는 힘이 커질 수 있습니다.",
    "신": "가까운 영역일수록 선을 분명히 하는 성향이 있어 조직에서도 역할 경계를 정리할 때 강점이 생깁니다.",
    "유": "혼자 결과를 다듬는 힘이 커서 문서와 마감 품질에서 차이를 만들기 쉬운 편입니다.",
    "술": "시간이 갈수록 책임감이 더 또렷해져 직장에서도 후반 관리력에서 강점이 보일 수 있습니다.",
    "해": "혼자 있을 때 여러 가능성을 넓게 보는 성향이 있어 직장 전환 타이밍을 오래 계산하는 편입니다.",
}

CAREER_PROFILE_HEADLINES = {
    "system_operator": "직장에서는 운영 기준을 세울수록 강점이 살아나는 관리형입니다.",
    "expansion_planner": "직장에서는 방향을 넓히고 판을 키울 때 힘이 붙는 확장형입니다.",
    "visible_driver": "직장에서는 존재감과 반응 속도가 성과로 이어지기 쉬운 추진형입니다.",
    "precision_builder": "직장에서는 정리, 완성도, 기준 설정이 경쟁력이 되는 정밀형입니다.",
    "strategic_observer": "직장에서는 한발 먼저 흐름을 읽고 움직일 때 차이가 나는 전략형입니다.",
    "coordination_manager": "직장에서는 조율과 연결을 통해 결과를 안정시키는 조정형입니다.",
}

CAREER_PROFILE_SUMMARIES = {
    "system_operator": "성과는 실무 감각보다 운영 기준을 얼마나 분명히 세우느냐에 따라 갈리기 쉽습니다.",
    "expansion_planner": "기회 자체는 보여도 어떤 판을 키울지 선택하는 방식이 결과를 크게 좌우합니다.",
    "visible_driver": "성과는 속도와 존재감을 어떻게 통제하느냐에 따라 훨씬 다르게 남을 수 있습니다.",
    "precision_builder": "작은 정리와 마감 품질이 누적될수록 직장 평판이 더 또렷하게 살아날 수 있습니다.",
    "strategic_observer": "서두르지 않고 흐름을 읽는 판단이 붙을수록 직장 선택의 질이 달라질 가능성이 큽니다.",
    "coordination_manager": "혼자 밀어붙이는 것보다 협업 구조를 정리할 때 성과가 훨씬 안정적으로 붙기 쉽습니다.",
}

CAREER_PROFILE_ADVICE = {
    "system_operator": "업무 기준표와 역할 경계를 먼저 정리한 뒤 움직이는 편이 직장 피로를 줄이는 데 도움이 됩니다.",
    "expansion_planner": "새 기회를 볼수록 지금 판을 왜 넓히는지 목적부터 적어 두는 편이 좋습니다.",
    "visible_driver": "실행 속도를 살리되 보고 순서와 말의 수위는 한 번 더 점검하는 편이 좋습니다.",
    "precision_builder": "완성도를 높이는 장점은 유지하되 끝내는 시점을 먼저 정해야 성과가 쌓입니다.",
    "strategic_observer": "크게 움직이기 전 작은 테스트나 비교표를 먼저 두는 편이 더 안정적입니다.",
    "coordination_manager": "관계 조율이 장점인 만큼 전부 떠안지 말고 연결과 위임을 함께 쓰는 편이 좋습니다.",
}

CAREER_STRENGTH_HEADLINE_CLAUSES = {
    "strong": [
        "역할이 커져도 버티는 힘이 있어 핵심 과제를 전진시키기 좋은 편입니다.",
        "압박 구간에서도 리듬을 유지하며 성과를 이어 가기 좋은 흐름입니다.",
        "책임이 늘어도 실행 밀도를 유지하기 쉬운 편입니다.",
        "중요한 결정을 실행까지 끌고 가기 유리한 에너지가 붙습니다.",
        "확장 과제를 맡아도 무너지지 않는 추진력이 살아 있습니다.",
    ],
    "slightly_strong": [
        "기본 버팀이 있어 핵심 과제 중심 운영이 유리합니다.",
        "초반 정리만 끝내면 중반 이후 실행 안정감이 커질 수 있습니다.",
        "무리하지 않아도 중요한 일은 성과로 연결되기 쉬운 흐름입니다.",
        "리듬만 지키면 업무 완성도를 유지하기 수월한 편입니다.",
        "우선순위를 좁혀 잡을수록 체감 성과가 선명해질 수 있습니다.",
    ],
    "balanced": [
        "확장과 관리의 균형을 맞출수록 직장운이 안정됩니다.",
        "속도와 정리 간격을 지키면 결과 편차를 줄이기 쉬운 흐름입니다.",
        "한쪽으로 몰아치지 않는 운영이 성과 품질을 지켜 줍니다.",
        "중간 점검 한 번이 전체 리듬을 크게 안정시킬 수 있습니다.",
        "작은 조정을 반복하는 방식이 장기 성과에 유리합니다.",
    ],
    "slightly_weak": [
        "범위를 줄여 핵심 업무만 남길수록 안정감이 커질 수 있습니다.",
        "확장보다 운영 정비를 먼저 두는 편이 더 유리합니다.",
        "결정 속도보다 확인 절차를 강화할수록 오차를 줄일 수 있습니다.",
        "한 번에 많이 벌리기보다 단계적으로 닫아 가는 편이 좋습니다.",
        "체력과 일정 상한선을 함께 잡아야 흐름을 지키기 쉽습니다.",
    ],
    "weak": [
        "올해는 방어 운영을 먼저 두는 선택이 실제로 더 유리합니다.",
        "무리한 확대보다 현재 범위 안정화가 먼저 맞는 흐름입니다.",
        "핵심 일정만 남기고 나머지를 조정할수록 손실을 줄이기 쉽습니다.",
        "속도를 낮추고 검증 빈도를 높이는 편이 안전합니다.",
        "역할·마감·체력 상한선을 숫자로 두는 운영이 필요합니다.",
    ],
}

CAREER_PATTERN_HEADLINE_CLAUSES = {
    "관성격": [
        "책임 분배와 기준 정리가 성과를 좌우하기 쉽습니다.",
        "역할 경계를 먼저 분명히 할수록 평판 리스크를 줄일 수 있습니다.",
        "평가와 신뢰가 함께 걸리는 장면에서 차이가 크게 벌어질 수 있습니다.",
    ],
    "재성격": [
        "성과 회수와 자원 배분 기준이 직장 결과를 크게 바꿀 수 있습니다.",
        "실적만 보지 말고 소모 대비 효율을 같이 봐야 하는 흐름입니다.",
        "시간·비용 대비 남는 일을 고르는 선별력이 중요해집니다.",
    ],
    "식상격": [
        "실행력과 산출물을 꾸준히 남기는 운영이 핵심입니다.",
        "아이디어보다 완료 기준 관리에서 성과 차이가 벌어질 수 있습니다.",
        "말보다 결과물로 증명하는 흐름이 강해지는 편입니다.",
    ],
    "인성격": [
        "정보·문서·근거 정리의 완성도가 결과를 좌우할 수 있습니다.",
        "준비 품질이 실행 안정성으로 이어지는 구조가 강하게 작동합니다.",
        "검토와 보완 절차를 고정하면 오차를 줄이기 쉬운 흐름입니다.",
    ],
    "비겁격": [
        "협업과 경쟁의 경계를 나누는 운영이 특히 중요해집니다.",
        "사람 변수 관리가 일정 품질만큼 중요한 해로 읽힙니다.",
        "주도권을 잡되 분산을 막는 구조 설계가 필요합니다.",
    ],
    "균형격": [
        "한쪽으로 치우치지 않는 운영이 가장 큰 강점으로 작동합니다.",
        "무리수보다 일관성이 성과를 키우는 흐름입니다.",
        "순서 관리만 잘해도 체감 난이도를 낮추기 쉽습니다.",
    ],
}

CAREER_STAR_HEADLINE_CLAUSES = {
    "비견": ["독립성과 주도권이 커져 역할 선택의 무게가 올라갈 수 있습니다.", "내 기준으로 밀고 가는 힘이 커질 수 있습니다."],
    "겁재": ["경쟁·분산 관리가 핵심이 되어 우선순위 선별이 중요해집니다.", "사람과 업무가 동시에 늘어 분산 리스크가 커질 수 있습니다."],
    "식신": ["실무 생산성과 마감 완성도를 올리기 좋은 흐름이 붙습니다.", "작은 결과를 반복 생산할수록 평가가 좋아질 수 있습니다."],
    "상관": ["표현력은 올라가지만 마찰 관리가 함께 필요해집니다.", "문제 제기와 개선 제안을 순서 있게 내는 편이 유리합니다."],
    "편재": ["외부 기회는 늘 수 있으나 선별 기준이 더 중요해집니다.", "제안이 많아질수록 잡을 일과 넘길 일을 나눠야 합니다."],
    "정재": ["관리형 성과가 쌓이기 좋은 흐름으로 운영 기준이 중요합니다.", "실적과 실무 균형을 맞추는 힘이 커질 수 있습니다."],
    "편관": ["압박 구간 대응력이 성패를 가르는 흐름이 강해집니다.", "도전 과제는 상한선 관리와 병행해야 안정적입니다."],
    "정관": ["책임·평가 이슈가 또렷해져 원칙 운영이 성과로 연결되기 쉽습니다.", "공적 역할에서 신뢰 축적이 중요한 해입니다."],
    "편인": ["방식 전환과 탐색 이슈가 올라와 실험 범위 관리가 필요합니다.", "새 접근을 시도하되 운영 리스크는 좁혀야 합니다."],
    "정인": ["준비·학습·근거 체계가 직장 안정도를 높여 줄 수 있습니다.", "기반 강화가 장기 성과로 이어지기 쉬운 흐름입니다."],
}

CAREER_HEADLINE_TEMPLATES = [
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

CAREER_SUMMARY_TEMPLATES = [
    "{profile} {tone}",
    "{profile} {trend}",
    "{profile} {strength}",
    "{tone} {star}",
    "{trend} {star}",
    "{strength} {pattern}",
    "{profile} {tone} {trend}",
    "{profile} {strength} {star}",
    "{tone} {pattern} {trend}",
    "{profile} {pattern} {tone}",
]

CAREER_HEADLINE_COOLDOWN_WINDOW = 2
_CAREER_RECENT_INDEXES: dict[str, deque[int]] = defaultdict(
    lambda: deque(maxlen=CAREER_HEADLINE_COOLDOWN_WINDOW)
)
_CAREER_HEADLINE_LOCK = Lock()


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


def _career_strength_key(analysis_context: dict | None) -> str:
    if not analysis_context:
        return "balanced"
    label = analysis_context.get("strength", {}).get("label", "balanced")
    return label if label in CAREER_STRENGTH_HEADLINE_CLAUSES else "balanced"


def _build_career_headline_candidates(
    *,
    saju_id: str,
    career_profile: str,
    tone: str,
    intensity: str,
    day_pillar_kor: str,
    current_stars: list[str],
    analysis_context: dict | None,
) -> list[str]:
    base_seed = _seed_from_values(
        saju_id,
        career_profile,
        tone,
        intensity,
        day_pillar_kor,
        current_stars[0] if current_stars else "",
        current_stars[1] if len(current_stars) > 1 else "",
        analysis_context.get("structure", {}).get("primary_pattern", "") if analysis_context else "",
        analysis_context.get("strength", {}).get("label", "") if analysis_context else "",
    )
    profile_sentence = CAREER_PROFILE_HEADLINES[career_profile]
    core_options = [
        _build_profile_headline(career_profile, tone, intensity, day_pillar_kor),
        profile_sentence,
        _build_headline(tone, intensity),
        f"{profile_sentence.rstrip('.')} 흐름이 올해 직장 판단의 축이 될 가능성이 큽니다.",
    ]
    pattern_key = (
        analysis_context.get("structure", {}).get("primary_pattern", "균형격")
        if analysis_context
        else "균형격"
    )
    pattern_options = CAREER_PATTERN_HEADLINE_CLAUSES.get(
        pattern_key,
        CAREER_PATTERN_HEADLINE_CLAUSES["균형격"],
    )
    strength_options = CAREER_STRENGTH_HEADLINE_CLAUSES[_career_strength_key(analysis_context)]
    star_options = CAREER_STAR_HEADLINE_CLAUSES.get(
        current_stars[0] if current_stars else "",
        CAREER_STAR_HEADLINE_CLAUSES["정인"],
    )
    if len(current_stars) > 1 and current_stars[1] in CAREER_STAR_HEADLINE_CLAUSES:
        star_options = [*star_options, *CAREER_STAR_HEADLINE_CLAUSES[current_stars[1]]]

    candidates: list[str] = []
    seen = set()
    for idx, template in enumerate(CAREER_HEADLINE_TEMPLATES):
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
    return candidates or [_build_profile_headline(career_profile, tone, intensity, day_pillar_kor)]


def _pick_career_headline(
    *,
    saju_id: str,
    career_profile: str,
    tone: str,
    intensity: str,
    day_pillar_kor: str,
    current_stars: list[str],
    analysis_context: dict | None,
) -> str:
    options = _build_career_headline_candidates(
        saju_id=saju_id,
        career_profile=career_profile,
        tone=tone,
        intensity=intensity,
        day_pillar_kor=day_pillar_kor,
        current_stars=current_stars,
        analysis_context=analysis_context,
    )
    seed = _seed_from_values(saju_id, career_profile, tone, intensity, *current_stars)
    base_index = seed % len(options)
    pattern_key = (
        analysis_context.get("structure", {}).get("primary_pattern", "균형격")
        if analysis_context
        else "균형격"
    )
    strength_key = _career_strength_key(analysis_context)
    cooldown_key = (
        f"{saju_id}:{career_profile}:{tone}:{intensity}:{'-'.join(current_stars)}:"
        f"{pattern_key}:{strength_key}"
    )
    with _CAREER_HEADLINE_LOCK:
        recent = _CAREER_RECENT_INDEXES[cooldown_key]
        selected_index = base_index
        if base_index in recent:
            for step in range(1, len(options)):
                candidate = (base_index + step) % len(options)
                if candidate not in recent:
                    selected_index = candidate
                    break
        recent.append(selected_index)
    return options[selected_index]


def _build_career_summary(
    *,
    saju_id: str,
    career_profile: str,
    tone: str,
    intensity: str,
    trend: str,
    current_stars: list[str],
    analysis_context: dict | None,
) -> str:
    seed = _seed_from_values(
        "career_summary",
        saju_id,
        career_profile,
        tone,
        intensity,
        trend,
        *current_stars,
        analysis_context.get("structure", {}).get("primary_pattern", "") if analysis_context else "",
        analysis_context.get("strength", {}).get("label", "") if analysis_context else "",
    )
    profile_clause = CAREER_PROFILE_SUMMARIES[career_profile].rstrip(".")
    tone_clause = _build_summary(tone, intensity).rstrip(".")
    trend_clause = f"올해 직장운에서는 {trend} 이슈가 실제 성과와 평판 차이를 만들기 쉬운 편입니다"
    star_clause = (
        f"연운 {current_stars[0]}와 대운 {current_stars[1]} 흐름이 겹쳐 운영 기준의 선명도가 더 중요해질 수 있습니다"
        if len(current_stars) >= 2
        else f"연운 {current_stars[0]} 흐름이 들어와 운영 방식의 선택이 중요해질 수 있습니다"
    )
    if analysis_context:
        strength_clause = (
            f"중간 계산 기준으로는 {analysis_context['strength']['display_label']} 구조라 "
            "역할과 일정 상한선을 먼저 나누는 편이 유리합니다"
        )
        pattern_clause = (
            f"핵심 구조가 {analysis_context['structure']['primary_pattern']}로 읽혀 "
            "기준과 순서를 먼저 고정하는 운영이 중요해질 수 있습니다"
        )
    else:
        strength_clause = "무리한 확장보다 현재 범위를 안정시키는 운영이 더 유리합니다"
        pattern_clause = "역할 기준을 먼저 세우는 편이 직장 피로를 줄이는 데 도움이 됩니다"

    template = CAREER_SUMMARY_TEMPLATES[seed % len(CAREER_SUMMARY_TEMPLATES)]
    summary = template.format(
        profile=profile_clause,
        tone=tone_clause,
        trend=trend_clause,
        strength=strength_clause,
        star=star_clause,
        pattern=pattern_clause,
    )
    return f"{' '.join(summary.split()).strip().rstrip('.')}."


def build_career_fortune(
    saju_result: dict,
    year_fortune: dict,
    analysis_context: dict | None = None,
) -> dict:
    """Build a rule-based career fortune from natal chart and current yearly flow."""
    saju = saju_result["saju"]
    day_stem = saju["day"]["stem"]
    day_pillar_kor = saju["day"]["kor"]
    month_branch = saju["month"]["branch"]
    year_stem = saju["year"]["stem"]
    time_branch = saju["time"]["branch"] if saju.get("time") else None
    ten_gods = calculate_ten_gods(saju)
    month_ten_god = ten_gods["ten_gods"]["month"]
    sentence_data = load_analysis_sentences()
    day_data = sentence_data["day_stem"][day_stem]
    month_data = sentence_data["month_branch"][month_branch]
    year_data = sentence_data["year_stem"][year_stem]
    time_data = sentence_data["time_branch"].get(time_branch) if time_branch else None
    month_ten_god_data = sentence_data["month_ten_god"].get(month_ten_god) if month_ten_god else None
    career_profile = _resolve_career_profile(day_stem, month_branch, month_ten_god)
    month_ten_god_career_line = (
        _pick(MONTH_TEN_GOD_CAREER_LINES[month_ten_god], len(day_pillar_kor) + len(month_ten_god))
        if month_ten_god
        else ""
    )
    day_pillar_line = _pick(
        get_day_pillar_sentence_options(day_pillar_kor, "career"),
        len(day_pillar_kor) + len(month_branch) + len(month_ten_god or ""),
    )

    current_stars = [year_fortune["ten_god"], year_fortune["daewoon_ten_god"]]
    saju_id = str(saju_result.get("saju_id", ""))
    intensity = _resolve_intensity(current_stars)
    tone = _resolve_tone(current_stars)
    trend = _resolve_trend(current_stars)
    advanced_lines = _analysis_context_career_lines(analysis_context)
    summary = _build_career_summary(
        saju_id=saju_id,
        career_profile=career_profile,
        tone=tone,
        intensity=intensity,
        trend=trend,
        current_stars=current_stars,
        analysis_context=analysis_context,
    )
    headline = _pick_career_headline(
        saju_id=saju_id,
        career_profile=career_profile,
        tone=tone,
        intensity=intensity,
        day_pillar_kor=day_pillar_kor,
        current_stars=current_stars,
        analysis_context=analysis_context,
    )
    explanation = f"{_build_explanation(current_stars, trend, tone)} {CAREER_PROFILE_SUMMARIES[career_profile]}"
    advice = f"{_build_advice(current_stars, tone)} {CAREER_PROFILE_ADVICE[career_profile]}"

    warning_seed = _seed_from_values(
        "career_warning",
        saju_id,
        day_stem,
        month_branch,
        time_branch or "",
        year_stem,
        *current_stars,
    )
    strengths = _pick_messages(current_stars, CAREER_STRENGTHS, limit=2, seed=warning_seed)
    warnings = _pick_messages(current_stars, CAREER_WARNINGS, limit=2, seed=warning_seed)
    strengths.extend(
        _dedupe(
            [
                _pick(month_data["work_adaptation"], len(trend)),
                DAY_STEM_CAREER_LINES[day_stem],
            ]
        )[:2]
    )
    warnings.extend(_extra_career_warnings(current_stars, month_branch, time_branch, seed=warning_seed))
    strengths.extend(advanced_lines["strengths"])
    warnings.extend(advanced_lines["warnings"])
    if not warnings:
        warnings = [CAREER_WARNING_FALLBACK]

    stripped_day_pillar_line = _strip_career_day_pillar_line(day_pillar_line).rstrip(".")

    context_easy_lines = [
        f"팀 안에서 누가 먼저 정리할지 애매한 장면에서는 {stripped_day_pillar_line}",
        *advanced_lines["easy"],
        _normalize_career_support_line(month_ten_god_career_line) if month_ten_god_career_line else "",
        CAREER_PROFILE_HEADLINES[career_profile],
        DAY_STEM_CAREER_LINES[day_stem],
        MONTH_BRANCH_CAREER_LINES[month_branch],
        YEAR_STEM_IMPRESSION_LINES[year_stem],
        _pick(day_data["social_reaction"], len(summary) + 7),
    ]
    context_easy_lines = [line for line in context_easy_lines if line]
    if month_ten_god_data:
        context_easy_lines.append(
            _normalize_career_support_line(
                _pick(month_ten_god_data["career_modifier"], len(headline) + 9).lower()
            )
        )

    context_real_lines = [
        f"역할이 겹치거나 누가 결정을 맡을지 애매한 장면에서는 {stripped_day_pillar_line}",
        *advanced_lines["real"],
        _pick(day_data["speech_style"], len(explanation) + 11),
        _pick(month_data["work_adaptation"], len(explanation) + 13),
        _pick(year_data["first_impression"], len(explanation) + 17),
    ]
    if time_data:
        context_real_lines.append(_pick(time_data["intimate_reaction"], len(explanation) + 19))
    if time_branch:
        context_real_lines.append(TIME_BRANCH_CAREER_LINES[time_branch])

    context_action_lines = [
        "올해는 욕심나는 일이 많아도 먼저 끝낼 일 세 가지만 정해 두는 편이 좋습니다.",
        "일이 겹칠수록 잘하는 일과 버릴 일을 먼저 가르는 편이 성과 분산을 줄이기 쉽습니다.",
        *advanced_lines["action"],
    ]

    section = build_career_section(
        headline=headline,
        explanation=explanation,
        advice=advice,
        strengths=_dedupe(strengths)[:2],
        warnings=_dedupe(warnings)[:2],
        seed=len("".join(current_stars)) + len(trend) + len(day_stem) + len(month_branch),
        context_easy_lines=context_easy_lines,
        context_real_lines=context_real_lines,
        context_action_lines=context_action_lines,
    )
    section["easy_explanation"] = [_normalize_career_support_line(line) for line in section["easy_explanation"]]
    section["explanation"] = " ".join(section["easy_explanation"])

    return {
        "headline": section["one_line"],
        "summary": summary,
        "explanation": " ".join(section["easy_explanation"]),
        "advice": " ".join(section["action_advice"]),
        "section": section,
        "trend": trend,
        "trend_kor": trend,
        "tone": tone,
        "tone_kor": {"positive": "안정형", "change": "변화형", "caution": "주의형"}[tone],
        "intensity": intensity,
        "intensity_kor": {"strong": "강", "medium": "보통", "light": "완만"}[intensity],
        "strengths": _dedupe(strengths)[:2],
        "warnings": _dedupe(warnings)[:2],
    }


def _resolve_intensity(stars: list[str]) -> str:
    if stars[0] == stars[1] or sum(star in CHANGE_STARS for star in stars) == 2:
        return "strong"
    if any(star in CHANGE_STARS for star in stars):
        return "medium"
    return "light"


def _resolve_tone(stars: list[str]) -> str:
    if any(star in CAUTION_STARS for star in stars):
        return "caution"
    if any(star in CHANGE_STARS for star in stars):
        return "change"
    return "positive"


def _resolve_trend(stars: list[str]) -> str:
    if "정관" in stars or "편관" in stars:
        return "평가/책임"
    if "편재" in stars or "정재" in stars:
        return "성과/관리"
    if "상관" in stars or "식신" in stars:
        return "표현/실행"
    return "유지/정비"


def _build_summary(tone: str, intensity: str) -> str:
    summary_map = {
        ("positive", "strong"): "올해는 조직 내 역할이 커지고 결과를 보여줄 자리가 선명하게 들어오는 흐름입니다.",
        ("positive", "medium"): "올해는 맡은 역할을 안정적으로 키워 가기 좋은 흐름입니다.",
        ("positive", "light"): "올해는 유지와 관리에 강점을 싣기 좋은 흐름입니다.",
        ("change", "strong"): "올해는 경쟁과 변화가 강해져 자리 이동이나 역할 전환 가능성까지 함께 보이는 흐름입니다.",
        ("change", "medium"): "올해는 변화 대응력이 직장운의 핵심이 되는 흐름입니다.",
        ("change", "light"): "올해는 작은 조정과 방식 전환이 성과에 연결되기 쉬운 흐름입니다.",
        ("caution", "strong"): "올해는 압박과 경쟁이 강해져 자리 변동 가능성까지 염두에 두고 움직여야 하는 흐름입니다.",
        ("caution", "medium"): "올해는 긴장감이 높아질 수 있어 속도보다 관리가 중요한 흐름입니다.",
        ("caution", "light"): "올해는 무리한 확장보다 현재 역할을 단단히 지키는 편이 좋은 흐름입니다.",
    }
    return summary_map[(tone, intensity)]


def _build_headline(tone: str, intensity: str) -> str:
    headline_map = {
        ("positive", "strong"): "성과와 책임이 동시에 커지는 시기입니다.",
        ("positive", "medium"): "성과와 관리 균형이 성과를 좌우합니다.",
        ("positive", "light"): "유지와 관리에 집중할수록 안정감이 커집니다.",
        ("change", "strong"): "기회는 많지만 선택이 성과를 좌우합니다.",
        ("change", "medium"): "변화 대응력이 올해 직장운의 핵심입니다.",
        ("change", "light"): "작은 조정이 일의 흐름을 바꿀 수 있습니다.",
        ("caution", "strong"): "경쟁이 강해져 자리 판단을 신중히 해야 합니다.",
        ("caution", "medium"): "무리한 확장보다 관리가 먼저인 해입니다.",
        ("caution", "light"): "현재 자리의 안정성을 지키는 편이 유리합니다.",
    }
    return headline_map[(tone, intensity)]


def _build_profile_headline(profile: str, tone: str, intensity: str, day_pillar_kor: str) -> str:
    tone_suffix = {
        ("positive", "strong"): "지금은 역할 확대를 받아낼 준비가 필요한 시기입니다.",
        ("positive", "medium"): "지금은 관리력과 결과를 함께 보여줘야 하는 시기입니다.",
        ("positive", "light"): "지금은 무리하게 넓히기보다 잘하는 방식을 고정할 시기입니다.",
        ("change", "strong"): "지금은 기회가 많아도 무엇을 잡을지 먼저 정해야 하는 시기입니다.",
        ("change", "medium"): "지금은 방식 조정이 실제 성과 차이로 이어지기 쉬운 시기입니다.",
        ("change", "light"): "지금은 작은 조정이 큰 손실을 줄이는 시기입니다.",
        ("caution", "strong"): "지금은 긴장 속에서도 판단 기준을 놓치지 않아야 하는 시기입니다.",
        ("caution", "medium"): "지금은 무리한 확대보다 운영 정비가 먼저인 시기입니다.",
        ("caution", "light"): "지금은 현재 자리의 완성도를 높이는 쪽이 더 맞는 시기입니다.",
    }[(tone, intensity)]
    headline_body = CAREER_PROFILE_HEADLINES[profile].replace("직장에서는 ", "").rstrip(".")
    return (
        f"역할이 커지거나 평가가 붙는 장면에서는 {day_pillar_kor} 일주의 결이 먼저 올라와 {headline_body}. "
        f"{tone_suffix}"
    )


def _pick_messages(stars: list[str], source: dict[str, str | list[str]], limit: int, *, seed: int = 0) -> list[str]:
    messages = []
    for star in stars:
        message = source.get(star)
        if isinstance(message, list):
            if not message:
                continue
            message = _pick(message, _seed_from_values(star, seed, len(messages)))
        if message and message not in messages:
            messages.append(message)
        if len(messages) >= limit:
            break
    return messages


def _build_explanation(stars: list[str], trend: str, tone: str) -> str:
    tone_phrase = {
        "positive": "맡은 일과 결과가 바로 이어지는 장면이 늘어",
        "change": "방식과 역할을 조정해야 하는 순간이 잦아",
        "caution": "압박과 평가가 함께 올라오기 쉬워",
    }[tone]
    return f"올해는 {tone_phrase} 직장에서는 {trend} 문제가 실제 성과와 평판 차이로 이어지기 쉬운 흐름입니다."


def _build_advice(stars: list[str], tone: str) -> str:
    if "편재" in stars:
        return "기회가 늘수록 바로 움직이기보다 기준에 맞는 일만 고르는 편이 좋습니다."
    if "겁재" in stars:
        return "경쟁이 강할수록 모든 일을 직접 쥐기보다 선택과 위임을 같이 쓰는 편이 좋습니다."
    if "정관" in stars or "편관" in stars:
        return "책임이 커질수록 속도보다 기준과 일정 관리에 힘을 두는 편이 좋습니다."
    if tone == "positive":
        return "올해는 실적을 조용히 쌓기보다 보이게 정리해 두는 편이 더 유리합니다."
    return "변화가 보여도 바로 갈아타기보다 현재 자리에서 관리 기준을 먼저 세우는 편이 좋습니다."


def _extra_career_warnings(stars: list[str], month_branch: str, time_branch: str | None, *, seed: int = 0) -> list[str]:
    warnings = []
    if month_branch in {"자", "해"}:
        warnings.append(_pick(MONTH_BRANCH_WATER_WARNING_VARIANTS, _seed_from_values(seed, month_branch, "water")))
    if month_branch in {"사", "오"}:
        warnings.append(_pick(MONTH_BRANCH_FIRE_WARNING_VARIANTS, _seed_from_values(seed, month_branch, "fire")))
    if time_branch in {"신", "유"}:
        warnings.append(_pick(TIME_BRANCH_METAL_WARNING_VARIANTS, _seed_from_values(seed, time_branch, "metal")))
    if "상관" in stars:
        warnings.append(_pick(STAR_SHANGGUAN_WARNING_VARIANTS, _seed_from_values(seed, "상관")))
    return warnings


def _pick(options: list[str], seed: int) -> str:
    return options[seed % len(options)]


def _resolve_career_profile(day_stem: str, month_branch: str, month_ten_god: str | None) -> str:
    if month_ten_god in {"정관", "정재"} or month_branch in {"축", "술"}:
        return "system_operator"
    if day_stem in {"갑", "을"} or month_branch in {"인", "묘"}:
        return "expansion_planner"
    if day_stem in {"병", "정"} or month_branch in {"사", "오"}:
        return "visible_driver"
    if day_stem in {"경", "신"} or month_branch in {"신", "유"}:
        return "precision_builder"
    if day_stem in {"임", "계"} or month_branch in {"자", "해"}:
        return "strategic_observer"
    return "coordination_manager"


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _analysis_context_career_lines(analysis_context: dict | None) -> dict[str, list[str]]:
    if not analysis_context:
        return {"easy": [], "real": [], "action": [], "strengths": [], "warnings": []}

    strength = analysis_context["strength"]
    yongshin = analysis_context["yongshin"]
    flags = analysis_context["flags"]
    interactions = analysis_context["interactions"]
    hidden_focus = flags.get("hidden_group_focus")

    easy_lines = [
        _career_strength_scene_line(strength),
        _career_yongshin_scene_line(yongshin),
    ]
    hidden_focus_line = _career_hidden_focus_line(hidden_focus)
    if hidden_focus_line:
        easy_lines.append(hidden_focus_line)

    real_lines: list[str] = []
    if interactions["with_daewoon"]:
        item = interactions["with_daewoon"][0]
        real_lines.append(f"역할이 바뀌거나 책임 범위가 넓어지는 시기에는 {item['meaning']}")
    if interactions["with_yearly"]:
        item = interactions["with_yearly"][0]
        real_lines.append(f"올해는 평가, 이동, 팀 변화가 겹치는 장면에서 {item['meaning']}")

    action_lines: list[str] = []
    action_lines.append(_career_action_support_line(flags, yongshin))

    strengths: list[str] = []
    warnings: list[str] = []
    if flags["is_day_master_strong"]:
        strengths.append("원국 기준으로는 한 번 맡은 일을 쉽게 놓치지 않는 편이라 책임이 커져도 버티는 힘이 남아 있는 편입니다.")
    if flags["is_day_master_weak"]:
        warnings.append(
            _pick(
                WEAK_WARNING_VARIANTS,
                _seed_from_values(
                    "career_warning_weak",
                    strength.get("label", ""),
                    yongshin.get("primary_candidate", ""),
                ),
            )
        )
    if flags["has_luck_pressure"]:
        warnings.append(
            _pick(
                LUCK_PRESSURE_WARNING_VARIANTS,
                _seed_from_values(
                    "career_warning_pressure",
                    strength.get("label", ""),
                    yongshin.get("secondary_candidate", ""),
                ),
            )
        )

    return {
        "easy": easy_lines,
        "real": real_lines,
        "action": action_lines,
        "strengths": strengths,
        "warnings": warnings,
    }
