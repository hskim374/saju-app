"""Yearly fortune calculation based on natal chart and daewoon."""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock

from services.interpretation_engine import build_yearly_section
from services.daewoon import get_active_daewoon_cycle
from services.saju_calculator import build_korean_datetime, get_year_month_pillars_for_datetime
from services.ten_gods import calculate_ten_god_for_stem

YEARLY_TEN_GOD_RULES = {
    "비견": {
        "headline": "주도권과 역할 조정이 중요한 해입니다.",
        "summary": "주도권과 역할 조정이 중요한 해입니다.",
        "explanation": "내 판단과 역할이 앞에 서기 쉬워 스스로 정한 기준이 실제 결과에 직접 연결되기 쉽습니다.",
        "advice": "내 주장만 세우기보다 협업 기준을 먼저 정하는 편이 좋습니다.",
        "focus": ["자기주도", "협업", "역할조정"],
    },
    "겁재": {
        "headline": "경쟁과 분산을 조절해야 하는 해입니다.",
        "summary": "경쟁과 분산을 조절해야 하는 해입니다.",
        "explanation": "사람과 기회가 동시에 늘 수 있지만 자원과 에너지도 쉽게 분산될 수 있는 해입니다.",
        "advice": "우선순위를 줄이고 지출과 관계 경계를 함께 관리하는 편이 좋습니다.",
        "focus": ["경쟁", "지출관리", "대인관계"],
    },
    "식신": {
        "headline": "실행력과 생산성을 끌어올리기 좋은 해입니다.",
        "summary": "실행력과 생산성을 끌어올리기 좋은 해입니다.",
        "explanation": "한 번 움직인 일이 실제 결과로 쌓이기 쉬워 생활 성과를 남기기 좋은 흐름입니다.",
        "advice": "기록과 결과 정리를 함께 하면 한 해의 성과가 더 또렷하게 남습니다.",
        "focus": ["성과", "실행", "생산성"],
    },
    "상관": {
        "headline": "표현과 변화가 강해지는 해입니다.",
        "summary": "표현과 변화가 강해지는 해입니다.",
        "explanation": "말과 방식의 힘이 강해져 변화 욕구가 커지지만 마찰도 함께 커질 수 있습니다.",
        "advice": "강한 표현은 한 번 정리해서 내보내는 편이 좋습니다.",
        "focus": ["변화", "표현", "조율"],
    },
    "편재": {
        "headline": "기회 포착과 대외 활동이 늘어나는 해입니다.",
        "summary": "기회 포착과 대외 활동이 늘어나는 해입니다.",
        "explanation": "밖에서 들어오는 제안과 접점이 늘어 활동 반경이 넓어지기 쉬운 해입니다.",
        "advice": "기회를 고르지 않으면 성과가 흩어지기 쉬우니 선별 기준이 필요합니다.",
        "focus": ["기회", "재물", "대외활동"],
    },
    "정재": {
        "headline": "안정적인 관리와 축적이 중요한 해입니다.",
        "summary": "안정적인 관리와 축적이 중요한 해입니다.",
        "explanation": "관리와 실무, 생활 기준을 정리할수록 실속이 쌓이기 쉬운 해입니다.",
        "advice": "예산과 시간표를 수치로 관리하면 장점이 더 크게 살아납니다.",
        "focus": ["안정", "축적", "실무"],
    },
    "편관": {
        "headline": "압박과 도전을 관리해야 하는 해입니다.",
        "summary": "압박과 도전을 관리해야 하는 해입니다.",
        "explanation": "긴장과 책임이 동시에 늘 수 있어 체감은 무겁지만 성장 압력도 커지는 해입니다.",
        "advice": "체력과 일정 상한선을 정해 두고 무리한 승부는 늦추는 편이 좋습니다.",
        "focus": ["도전", "규율", "긴장관리"],
    },
    "정관": {
        "headline": "책임과 평가가 부각되는 해입니다.",
        "summary": "책임과 평가가 부각되는 해입니다.",
        "explanation": "조직과 책임의 무게가 커져 평판과 역할이 더 또렷하게 보이기 쉬운 해입니다.",
        "advice": "기준과 원칙을 먼저 세우면 부담이 신뢰로 바뀌기 쉽습니다.",
        "focus": ["직장", "책임", "평가"],
    },
    "편인": {
        "headline": "전환과 직관이 함께 작동하는 해입니다.",
        "summary": "전환과 직관이 함께 작동하는 해입니다.",
        "explanation": "기존 방식이 답답해져 다른 시각과 새로운 선택지를 찾게 되는 해입니다.",
        "advice": "실험 범위를 좁혀 두면 전환이 더 안정적으로 이어집니다.",
        "focus": ["전환", "직관", "탐색"],
    },
    "정인": {
        "headline": "배움과 지원 기반을 다지기 좋은 해입니다.",
        "summary": "배움과 지원 기반을 다지기 좋은 해입니다.",
        "explanation": "준비와 배움, 자료 축적이 실제 안정감으로 이어지기 쉬운 해입니다.",
        "advice": "확장보다 준비와 자격, 자료 정리에 시간을 쓰는 편이 좋습니다.",
        "focus": ["학습", "지원", "안정"],
    },
}

YEARLY_HEADLINE_SUFFIXES = [
    "초반 우선순위만 선명하게 잡아도 체감이 크게 달라질 수 있습니다.",
    "상반기에는 기준 정리, 하반기에는 실행 밀도 관리가 더 중요해질 수 있습니다.",
    "큰 선택은 속도보다 지속 가능성을 먼저 점검할수록 유리할 수 있습니다.",
    "사람·일정·돈이 겹치는 구간에서는 범위를 줄일수록 안정감을 지키기 쉽습니다.",
    "한 번에 많이 벌리기보다 핵심 두세 가지를 깊게 가져가는 편이 맞습니다.",
    "중간 점검 한 번만 넣어도 실수와 소모를 함께 줄이기 쉬운 흐름입니다.",
    "기준을 문장으로 남겨 두면 흔들리는 장면에서도 판단이 훨씬 선명해질 수 있습니다.",
    "확정할 일과 보류할 일을 분리하면 운영 피로를 크게 낮추기 쉽습니다.",
    "좋은 흐름이 보여도 선별 기준을 지킬 때 결과 편차가 줄어드는 해입니다.",
]

YEARLY_HEADLINE_COOLDOWN_WINDOW = 2
_YEARLY_RECENT_INDEXES: dict[str, deque[int]] = defaultdict(
    lambda: deque(maxlen=YEARLY_HEADLINE_COOLDOWN_WINDOW)
)
_YEARLY_VARIANT_LOCK = Lock()

YEARLY_STRENGTH_HEADLINE_CLAUSES = {
    "strong": [
        "체력과 추진력이 받쳐 줘 큰 틀을 밀기 좋은 흐름입니다",
        "핵심 과제를 전진시키기 좋은 버팀이 확보되는 해입니다",
        "압박이 와도 페이스를 유지하며 성과를 이어 가기 쉬운 구간입니다",
        "주도권을 잡고 실행 속도를 끌어올리기 수월한 해입니다",
        "확장 과제를 맡아도 무너지지 않는 버티는 힘이 있는 편입니다",
        "중요한 결정을 실행까지 연결하기 비교적 유리한 흐름입니다",
        "업무와 생활 리듬을 동시에 끌고 가기 좋은 에너지가 붙습니다",
        "판단 이후 행동으로 넘어가는 속도가 잘 살아나는 해입니다",
        "큰일을 작게 쪼개 추진하면 완성도와 속도를 함께 잡기 쉽습니다",
        "실행 부담이 있어도 구조를 유지하며 결과를 남기기 좋습니다",
    ],
    "slightly_strong": [
        "기본 버팀이 있어 핵심 과제는 꾸준히 밀어붙이기 좋습니다",
        "초반 정리만 해 두면 중반 이후 실행이 훨씬 수월해집니다",
        "크게 무리하지 않아도 중요한 일은 성과로 연결되기 쉽습니다",
        "리듬만 흔들리지 않으면 실행 안정감이 유지되는 편입니다",
        "부담이 와도 우선순위를 지키면 흐름이 쉽게 무너지지 않습니다",
        "핵심 목표를 좁혀 잡으면 체감 성과가 빠르게 올라옵니다",
        "기준을 먼저 세우면 추진력과 완성도를 함께 가져가기 좋습니다",
        "한 번 정한 방향을 끝까지 밀어 주기 좋은 힘이 있습니다",
        "관리와 실행을 병행해도 과부하를 줄이기 쉬운 흐름입니다",
        "선택을 줄이고 집중하면 결과 편차를 작게 만들 수 있습니다",
    ],
    "balanced": [
        "확장과 관리의 균형을 맞출수록 결과 품질이 안정됩니다",
        "속도와 정리의 간격을 지키면 무난한 성과를 이어 가기 쉽습니다",
        "한쪽으로 치우치지 않게 운영하면 체감 부담이 크게 줄어듭니다",
        "중간 점검을 넣으면 변동 구간에서도 안정적으로 마감하기 좋습니다",
        "큰 무리 없이도 기준을 지키는 운영에서 성과가 쌓이는 해입니다",
        "리듬을 유지하는 습관이 결과 편차를 줄이는 핵심이 됩니다",
        "과감한 선택보다 일관된 기준이 더 큰 차이를 만드는 흐름입니다",
        "우선순위를 명확히 하면 기회와 부담을 함께 관리하기 좋습니다",
        "실행과 회복 구간을 분리하면 장기 페이스를 지키기 쉽습니다",
        "조금씩 쌓는 방식이 연말 체감 성과를 키우기 유리합니다",
    ],
    "slightly_weak": [
        "무리한 확장보다 범위 관리에 집중할수록 안정감이 커집니다",
        "해야 할 일을 줄여 선명하게 잡으면 과부하를 피하기 쉽습니다",
        "초반에 기준을 고정하면 중반 이후 흔들림을 줄일 수 있습니다",
        "중요한 결정은 한 박자 늦춰 확인하면 오차를 줄이기 좋습니다",
        "체력과 일정 상한선을 정하면 소모를 크게 줄일 수 있습니다",
        "넓게 벌리기보다 핵심 과제 중심으로 운영하는 편이 유리합니다",
        "작은 완성 단위를 반복하는 방식이 피로를 줄이고 성과를 남깁니다",
        "새로운 일 추가보다 기존 흐름 정리에 집중할 때 결과가 낫습니다",
        "확정과 보류를 분리하면 판단 피로를 안정적으로 관리할 수 있습니다",
        "속도보다 정확도를 먼저 두는 선택이 전체 흐름을 지켜 줍니다",
    ],
    "weak": [
        "올해는 방어와 회복을 우선에 두는 운영이 실제로 더 유리합니다",
        "한 번에 많이 벌리기보다 손실을 줄이는 전략이 먼저 맞습니다",
        "핵심 일정만 남기고 나머지는 조정하는 편이 안정적입니다",
        "무리한 승부보다 리듬 회복에 집중해야 결과 편차를 줄일 수 있습니다",
        "과감한 확장보다 기반 보강이 장기적으로 훨씬 유리한 흐름입니다",
        "속도를 낮추고 점검 빈도를 올리면 흔들림을 줄이기 쉽습니다",
        "한계선을 먼저 정하면 부담 구간에서도 버티는 힘이 남습니다",
        "일정과 사람 이슈를 동시에 줄이는 방식이 안전한 해입니다",
        "결정은 작게 쪼개고 실행은 순차로 두는 편이 손실을 줄입니다",
        "확정 숫자를 줄이고 보류를 늘리는 운영이 실제 체감에 유리합니다",
    ],
}

YEARLY_PATTERN_HEADLINE_CLAUSES = {
    "관성격": [
        "책임 분배와 기준 정리가 성패를 가르는 축이 됩니다",
        "역할 경계와 마감 기준을 명확히 할수록 안정성이 커집니다",
        "평가와 신뢰가 함께 걸리는 장면에서 결과 차이가 커질 수 있습니다",
        "원칙을 먼저 세운 운영이 전체 리듬을 지키는 핵심이 됩니다",
        "압박 상황에서도 기준 유지가 성과를 만드는 구조입니다",
        "조직 안에서 신뢰를 쌓는 방식이 직접 성과로 이어지기 쉽습니다",
        "무리한 확장보다 책임 범위 정리가 먼저 필요한 흐름입니다",
        "역할 충돌을 줄일수록 체감 피로가 빠르게 내려갈 수 있습니다",
        "규율과 유연성의 균형이 중요한 해로 읽히는 편입니다",
        "기준과 절차를 선행할수록 변동성 대응이 쉬워집니다",
    ],
    "재성격": [
        "돈과 자원 운영의 기준을 세우는 힘이 핵심 경쟁력이 됩니다",
        "수익보다 보존 규칙을 먼저 잡을수록 실속이 더 남습니다",
        "지출·투자 판단에서 선별 기준의 차이가 크게 벌어질 수 있습니다",
        "현금흐름 관리가 전체 안정도를 좌우하는 해로 읽힙니다",
        "재무 의사결정의 속도보다 조건 검증이 더 중요해집니다",
        "기회가 많아도 걸러내는 기준이 성과 편차를 줄여 줍니다",
        "고정비 관리와 누수 점검이 실전 결과를 크게 바꿉니다",
        "자원 배분의 선명도가 연말 성과를 가르는 흐름입니다",
        "확장보다 수익 구조 다듬기에 강점이 살아나는 해입니다",
        "수익 회수와 비용 통제를 같이 가져갈 때 체감이 좋아집니다",
    ],
    "식상격": [
        "실행력과 산출물을 얼마나 꾸준히 남기느냐가 핵심입니다",
        "아이디어보다 완료 단위 관리가 성과를 키우는 구조입니다",
        "표현과 생산의 리듬을 지키면 결과가 빠르게 쌓일 수 있습니다",
        "시도 횟수보다 마감 품질에서 차이가 벌어지기 쉽습니다",
        "실행 속도와 검수 절차를 함께 두는 편이 유리합니다",
        "작은 결과를 반복 생산하는 방식이 올해 특히 잘 맞습니다",
        "과도한 확산보다 핵심 결과물 집중이 성과를 키웁니다",
        "말보다 산출물로 증명하는 흐름이 강해지는 해입니다",
        "기획과 실행의 간격을 줄일수록 체감 성과가 커질 수 있습니다",
        "완료 기준을 먼저 세우면 실행 피로를 줄이고 품질을 지킬 수 있습니다",
    ],
    "인성격": [
        "정보 정리와 학습 기반을 다지는 운영이 특히 중요해집니다",
        "준비의 질이 실행 결과를 좌우하는 구조가 강하게 작동합니다",
        "검토와 보완 과정을 잘 설계할수록 오차를 줄이기 쉽습니다",
        "자료·문서·기록 관리가 성과 안정성을 끌어올릴 수 있습니다",
        "성급한 결론보다 근거 정리가 더 큰 차이를 만듭니다",
        "배움과 재정비를 병행할 때 체감 불안이 줄어드는 해입니다",
        "지식 축적을 실전 규칙으로 연결하는 과정이 핵심이 됩니다",
        "준비 시간을 짧게라도 고정하면 흐름을 잃지 않기 쉽습니다",
        "기초 체계를 다지는 선택이 장기 성과에 유리하게 작동합니다",
        "정보 과부하를 줄이고 핵심만 남길수록 실행 전환이 쉬워집니다",
    ],
    "비겁격": [
        "협업과 경쟁의 경계를 어떻게 잡느냐가 중요한 해입니다",
        "사람 흐름이 커질수록 역할 선명도가 성과를 좌우할 수 있습니다",
        "관계 에너지 관리가 일정 운영 품질을 크게 바꿀 수 있습니다",
        "주도권을 잡되 분산을 막는 운영이 핵심이 됩니다",
        "같이 가는 일과 혼자 하는 일을 구분할수록 안정적입니다",
        "경쟁 장면에서 기준 유지가 결과 편차를 줄이는 구조입니다",
        "과열된 대인 흐름을 조절하면 소모를 크게 줄일 수 있습니다",
        "협업 구조를 먼저 정하면 시행착오를 줄이기 쉽습니다",
        "관계 변수 관리가 성과 관리만큼 중요한 해로 읽힙니다",
        "주도성과 조율을 함께 가져갈 때 체감 성과가 좋아집니다",
    ],
    "균형격": [
        "한쪽으로 치우치지 않는 운영이 가장 큰 강점으로 작동합니다",
        "균형 유지가 곧 성과 안정으로 연결되기 쉬운 해입니다",
        "크게 흔들리지 않는 기준 관리가 결과 품질을 지켜 줍니다",
        "확장과 방어를 구간별로 나누는 편이 유리합니다",
        "중간 점검을 넣는 습관이 전체 리듬을 안정시킵니다",
        "작은 조정의 누적이 큰 편차를 줄이는 핵심이 됩니다",
        "일정·관계·재무 균형을 함께 보는 운영이 맞습니다",
        "무리수보다 일관성이 성과를 키우는 구조입니다",
        "순서 관리만 잘해도 체감 난이도를 낮추기 쉽습니다",
        "변동 구간에서도 기본 틀을 지키는 힘이 중요한 해입니다",
    ],
}

YEARLY_DAEWOON_HEADLINE_CLAUSES = {
    "비견": [
        "대운의 비견 흐름이 겹쳐 독립성과 주도권이 더 강해질 수 있습니다",
        "대운에서 비견이 받쳐 자기 기준으로 밀고 가는 힘이 커질 수 있습니다",
        "대운 비견 영향으로 스스로 결정하고 실행하는 장면이 늘기 쉽습니다",
        "대운 비견이 겹쳐 역할 주도권을 직접 잡는 흐름이 강화됩니다",
        "대운 비견 흐름이 더해져 독자 판단의 비중이 커지기 쉬운 시기입니다",
    ],
    "겁재": [
        "대운의 겁재 기운이 겹쳐 사람·기회 분산 관리가 특히 중요해집니다",
        "대운에서 겁재가 실려 자원 분산을 막는 운영이 핵심이 됩니다",
        "대운 겁재 영향으로 경쟁과 협업 변수가 함께 커질 수 있습니다",
        "대운 겁재가 겹쳐 우선순위 선별이 성과 편차를 줄이는 열쇠가 됩니다",
        "대운 겁재 흐름으로 대인 이슈를 구조적으로 관리할 필요가 큽니다",
    ],
    "식신": [
        "대운의 식신 흐름이 겹쳐 실행·산출 기회가 더 자주 열릴 수 있습니다",
        "대운 식신 영향으로 작은 결과를 꾸준히 남길수록 유리해집니다",
        "대운 식신이 더해져 실무 생산성 강화 구간이 길어질 수 있습니다",
        "대운 식신 흐름 덕분에 손에 잡히는 성과를 만들기 쉬운 편입니다",
        "대운 식신 기운이 겹쳐 실행 리듬만 지키면 결과가 잘 쌓일 수 있습니다",
    ],
    "상관": [
        "대운의 상관 흐름이 겹쳐 변화·표현 이슈가 더 크게 체감될 수 있습니다",
        "대운 상관 영향으로 말과 방식의 강도를 조절하는 운영이 중요합니다",
        "대운 상관이 더해져 기존 틀을 바꾸는 압력이 커질 수 있습니다",
        "대운 상관 흐름으로 표현력은 올라가지만 마찰 관리가 필요합니다",
        "대운 상관 기운이 겹쳐 변화를 성과로 연결하는 설계가 중요해집니다",
    ],
    "편재": [
        "대운의 편재 흐름이 겹쳐 대외 기회 선별력이 더 중요해집니다",
        "대운 편재 영향으로 제안과 접점이 늘어도 기준 유지가 핵심입니다",
        "대운 편재가 더해져 기회 포착은 쉬워지나 분산 리스크도 커질 수 있습니다",
        "대운 편재 흐름으로 밖에서 들어오는 흐름을 고르는 힘이 필요합니다",
        "대운 편재 기운이 겹쳐 실속 중심 선별 운영이 더 유리해집니다",
    ],
    "정재": [
        "대운의 정재 흐름이 겹쳐 관리·축적 운영의 안정감이 커질 수 있습니다",
        "대운 정재 영향으로 재무·생활 기준 정리가 더 큰 성과를 만듭니다",
        "대운 정재가 더해져 실무형 안정 운영이 유리하게 작동합니다",
        "대운 정재 흐름으로 숫자 기반 관리의 효과가 커질 수 있습니다",
        "대운 정재 기운이 겹쳐 실속 중심 운영이 장기적으로 유리합니다",
    ],
    "편관": [
        "대운의 편관 흐름이 겹쳐 압박 구간에서 체력 배분이 중요해집니다",
        "대운 편관 영향으로 도전 과제 대응에 상한선 관리가 필요합니다",
        "대운 편관이 더해져 긴장·책임 이슈가 커질 수 있어 방어 설계가 필요합니다",
        "대운 편관 흐름으로 강한 추진보다 안정적 리듬 유지가 중요합니다",
        "대운 편관 기운이 겹쳐 무리한 승부를 줄이는 선택이 유리합니다",
    ],
    "정관": [
        "대운의 정관 흐름이 겹쳐 책임·평가 이슈가 더 뚜렷해질 수 있습니다",
        "대운 정관 영향으로 원칙과 절차 운영이 신뢰를 크게 키울 수 있습니다",
        "대운 정관이 더해져 공적 역할 관리가 중요한 시기가 이어집니다",
        "대운 정관 흐름으로 기준 유지가 직접 성과로 연결되기 쉽습니다",
        "대운 정관 기운이 겹쳐 책임 분배 설계의 중요도가 높아집니다",
    ],
    "편인": [
        "대운의 편인 흐름이 겹쳐 전환·탐색 이슈가 더 자주 올라올 수 있습니다",
        "대운 편인 영향으로 기존 방식 재정비 필요성이 커질 수 있습니다",
        "대운 편인 흐름이 더해져 새로운 관점 실험이 중요해지는 시기입니다",
        "대운 편인 기운이 겹쳐 선택지 관리와 우선순위 정리가 핵심입니다",
        "대운 편인 영향으로 전환 속도를 조절하는 운영이 유리해집니다",
    ],
    "정인": [
        "대운의 정인 흐름이 겹쳐 학습·준비·지원 체계가 성과를 키울 수 있습니다",
        "대운 정인 영향으로 기초를 다지는 선택이 더 유리하게 작동합니다",
        "대운 정인이 더해져 준비 품질이 실전 안정성으로 이어지기 쉽습니다",
        "대운 정인 흐름으로 문서·근거·체계 정비의 효과가 커질 수 있습니다",
        "대운 정인 기운이 겹쳐 확장보다 기반 강화가 더 유리해집니다",
    ],
}

YEARLY_PROFILE_HEADLINE_CLAUSES = {
    "expansion": [
        "공격적 확장보다 선별 확장이 성과 효율을 높이기 쉽습니다",
        "기회를 좁혀 잡을수록 결과 품질이 빠르게 올라갈 수 있습니다",
        "확장 장면에서도 기준 유지가 장기 편차를 줄이는 핵심입니다",
        "한 번에 넓히기보다 단계 확장이 더 안전하고 효과적입니다",
        "성과를 키우되 소모를 통제하는 운영이 맞는 해입니다",
    ],
    "stability": [
        "조직과 생활의 기본 틀을 안정시키는 선택이 더 유리합니다",
        "기준 문서화와 마감 습관이 체감 난이도를 낮춰 줄 수 있습니다",
        "무리한 변화보다 운영 안정도를 높이는 쪽이 맞습니다",
        "책임 구간을 미리 나누면 리스크를 크게 줄일 수 있습니다",
        "안정된 페이스를 유지할수록 연말 성과가 분명해질 수 있습니다",
    ],
    "defense": [
        "리스크를 줄이는 방어 운영이 올해 체감을 가장 크게 바꿉니다",
        "속도보다 안전장치가 결과 편차를 줄이는 핵심입니다",
        "손실 가능성을 먼저 줄이는 선택이 전체 흐름을 지켜 줍니다",
        "변수 대응력을 높이는 운영이 실전 안정성을 키울 수 있습니다",
        "무리수를 줄이고 검증 빈도를 높이는 방식이 특히 유리합니다",
    ],
    "coordination": [
        "사람·일정·자원 조율의 완성도가 성과를 좌우하기 쉽습니다",
        "조율 순서를 먼저 잡을수록 마찰과 소모를 함께 줄일 수 있습니다",
        "관계와 실행의 간격을 맞추는 운영이 효과적입니다",
        "결론 속도보다 합의 순서 관리가 체감 결과를 바꿀 수 있습니다",
        "협업 장면에서 기준 공유를 먼저 두는 편이 유리합니다",
    ],
    "recovery": [
        "기반 회복을 먼저 두는 운영이 하반기 체감을 크게 바꿀 수 있습니다",
        "복구 가능한 범위 안에서 움직일수록 안정감이 높아집니다",
        "회복 루틴을 고정하면 변동 구간에서도 버티는 힘이 남습니다",
        "무리한 확장보다 체력·일정 회복이 우선인 해로 읽힙니다",
        "기초 리듬 복원이 선행될수록 실행 품질이 다시 올라옵니다",
    ],
}

YEARLY_HEADLINE_TEMPLATES = [
    "{core}. {pattern}.",
    "{core}. {strength}.",
    "{core}. {profile}.",
    "{core}. {daewoon}.",
    "{pattern}. {strength}.",
    "{pattern}. {profile}.",
    "{strength}. {daewoon}.",
    "{profile}. {daewoon}.",
    "{core}. {pattern}. {profile}.",
    "{core}. {strength}. {daewoon}.",
]

YEARLY_SUMMARY_TEMPLATES = [
    "{core}. {daewoon}.",
    "{core}. {strength}.",
    "{core}. {focus}.",
    "{core}. {advanced}.",
    "{daewoon}. {strength}.",
    "{daewoon}. {focus}.",
    "{strength}. {focus}.",
    "{core}. {daewoon}. {focus}.",
    "{core}. {strength}. {advanced}.",
    "{core}. {daewoon}. {strength}.",
]


def _expand_yearly_headline_variants(base: str) -> list[str]:
    normalized_base = base.strip().rstrip(".")
    variants = [f"{normalized_base}."]
    for suffix in YEARLY_HEADLINE_SUFFIXES:
        variants.append(f"{normalized_base}. {suffix}")
    return variants[:10]


YEARLY_HEADLINE_VARIANTS = {
    key: _expand_yearly_headline_variants(rule["headline"])
    for key, rule in YEARLY_TEN_GOD_RULES.items()
}


def _yearly_variant_seed(*parts: object) -> int:
    total = 0
    for part in parts:
        if part is None:
            continue
        text = str(part)
        total += sum(ord(char) for char in text)
    return total


def _pick_by_seed(options: list[str], seed: int) -> str:
    if not options:
        return ""
    return options[seed % len(options)]


def _resolve_yearly_profile_key(
    *,
    analysis_context: dict | None,
    year_ten_god: str,
    daewoon_ten_god: str,
) -> str:
    if not analysis_context:
        if year_ten_god in {"식신", "상관", "편재", "정재"}:
            return "expansion"
        if year_ten_god in {"편관", "정관"}:
            return "stability"
        return "coordination"

    flags = analysis_context.get("flags", {})
    strength_label = analysis_context.get("strength", {}).get("label", "balanced")
    if flags.get("has_luck_pressure") or flags.get("has_branch_conflict"):
        return "defense"
    if strength_label in {"weak", "slightly_weak"} and flags.get("needs_resource_support"):
        return "recovery"
    if year_ten_god in {"식신", "상관", "편재", "정재"} and daewoon_ten_god in {"식신", "상관", "편재", "정재"}:
        return "expansion"
    if year_ten_god in {"편관", "정관", "정인", "편인"}:
        return "stability"
    return "coordination"


def _build_yearly_headline_candidates(
    *,
    year_ten_god: str,
    daewoon_ten_god: str,
    target_year: int,
    saju_id: str,
    analysis_context: dict | None,
) -> list[str]:
    base_seed = _yearly_variant_seed(
        saju_id,
        target_year,
        year_ten_god,
        daewoon_ten_god,
        analysis_context.get("strength", {}).get("label", "") if analysis_context else "",
        analysis_context.get("structure", {}).get("primary_pattern", "") if analysis_context else "",
    )
    primary_pattern = (
        analysis_context.get("structure", {}).get("primary_pattern", "균형격")
        if analysis_context
        else "균형격"
    )
    strength_label = (
        analysis_context.get("strength", {}).get("label", "balanced")
        if analysis_context
        else "balanced"
    )
    profile_key = _resolve_yearly_profile_key(
        analysis_context=analysis_context,
        year_ten_god=year_ten_god,
        daewoon_ten_god=daewoon_ten_god,
    )
    core_options = YEARLY_HEADLINE_VARIANTS.get(
        year_ten_god,
        [YEARLY_TEN_GOD_RULES[year_ten_god]["headline"]],
    )
    pattern_options = YEARLY_PATTERN_HEADLINE_CLAUSES.get(
        primary_pattern,
        YEARLY_PATTERN_HEADLINE_CLAUSES["균형격"],
    )
    strength_options = YEARLY_STRENGTH_HEADLINE_CLAUSES.get(
        strength_label,
        YEARLY_STRENGTH_HEADLINE_CLAUSES["balanced"],
    )
    daewoon_options = YEARLY_DAEWOON_HEADLINE_CLAUSES.get(
        daewoon_ten_god,
        YEARLY_DAEWOON_HEADLINE_CLAUSES["정인"],
    )
    profile_options = YEARLY_PROFILE_HEADLINE_CLAUSES.get(
        profile_key,
        YEARLY_PROFILE_HEADLINE_CLAUSES["coordination"],
    )
    candidates: list[str] = []
    seen = set()
    for idx, template in enumerate(YEARLY_HEADLINE_TEMPLATES):
        sentence = template.format(
            core=_pick_by_seed(core_options, base_seed + idx * 3 + 1).rstrip("."),
            pattern=_pick_by_seed(pattern_options, base_seed + idx * 5 + 2).rstrip("."),
            strength=_pick_by_seed(strength_options, base_seed + idx * 7 + 3).rstrip("."),
            daewoon=_pick_by_seed(daewoon_options, base_seed + idx * 11 + 4).rstrip("."),
            profile=_pick_by_seed(profile_options, base_seed + idx * 13 + 5).rstrip("."),
        )
        sentence = " ".join(sentence.split())
        if sentence not in seen:
            seen.add(sentence)
            candidates.append(sentence)
    return candidates or [YEARLY_TEN_GOD_RULES[year_ten_god]["headline"]]


def _pick_yearly_headline(
    *,
    year_ten_god: str,
    daewoon_ten_god: str,
    target_year: int,
    saju_id: str,
    analysis_context: dict | None,
) -> str:
    options = _build_yearly_headline_candidates(
        year_ten_god=year_ten_god,
        daewoon_ten_god=daewoon_ten_god,
        target_year=target_year,
        saju_id=saju_id,
        analysis_context=analysis_context,
    )
    seed = _yearly_variant_seed(saju_id, target_year, year_ten_god, daewoon_ten_god)
    base_index = seed % len(options)
    cooldown_key = f"{saju_id}:{target_year}:{year_ten_god}:{daewoon_ten_god}"
    with _YEARLY_VARIANT_LOCK:
        recent = _YEARLY_RECENT_INDEXES[cooldown_key]
        selected_index = base_index
        if base_index in recent:
            for step in range(1, len(options)):
                candidate = (base_index + step) % len(options)
                if candidate not in recent:
                    selected_index = candidate
                    break
        recent.append(selected_index)
    return options[selected_index]


def _build_yearly_summary(
    *,
    year_rule: dict,
    daewoon_rule: dict,
    year_ten_god: str,
    daewoon_ten_god: str,
    target_year: int,
    saju_id: str,
    focus: list[str],
    advanced: dict,
    analysis_context: dict | None,
) -> str:
    seed = _yearly_variant_seed(
        "yearly_summary",
        saju_id,
        target_year,
        year_ten_god,
        daewoon_ten_god,
        analysis_context.get("structure", {}).get("primary_pattern", "") if analysis_context else "",
        analysis_context.get("strength", {}).get("label", "") if analysis_context else "",
    )
    core_clause = year_rule["summary"].rstrip(".")
    daewoon_clause = f"대운에서는 {daewoon_rule['focus'][0]} 흐름이 겹칩니다"
    if analysis_context:
        strength_clause = (
            f"중간 계산 기준으로는 {analysis_context['strength']['display_label']} 쪽이라 "
            "운영 기준을 먼저 세우는 편이 유리합니다"
        )
        pattern_clause = (
            f"핵심 구조가 {analysis_context['structure']['primary_pattern']}로 읽혀 "
            "우선순위 분리가 중요해질 수 있습니다"
        )
    else:
        strength_clause = "큰 선택은 속도보다 유지 가능성을 먼저 점검하는 편이 좋습니다"
        pattern_clause = "기준과 순서를 먼저 고정하면 체감 흔들림을 줄이기 쉽습니다"
    focus_clause = (
        f"특히 올해는 {focus[0]}보다 {focus[1] if len(focus) > 1 else focus[0]}을 먼저 정리하는 편이 좋습니다"
        if focus
        else "올해는 확장보다 운영 기준 정리가 체감 차이를 만들기 쉽습니다"
    )
    advanced_clause = (advanced.get("summary") or pattern_clause).rstrip(".")
    clauses = {
        "core": core_clause,
        "daewoon": daewoon_clause,
        "strength": strength_clause.rstrip("."),
        "focus": focus_clause.rstrip("."),
        "advanced": advanced_clause,
    }
    template = YEARLY_SUMMARY_TEMPLATES[seed % len(YEARLY_SUMMARY_TEMPLATES)]
    summary = template.format(**clauses)
    return f"{' '.join(summary.split()).strip().rstrip('.')}."


def calculate_yearly_fortune(
    saju_result: dict,
    daewoon: dict,
    target_year: int,
    analysis_context: dict | None = None,
) -> dict:
    """Build a yearly fortune summary from the target year's annual pillar."""
    reference_moment = build_korean_datetime(target_year, 7, 1, 12, 0)
    year_pillar = get_year_month_pillars_for_datetime(reference_moment)["year"]
    day_stem = saju_result["saju"]["day"]["stem"]
    year_ten_god = calculate_ten_god_for_stem(day_stem, year_pillar["stem"])
    nominal_age = max(1, target_year - saju_result["resolved_solar"]["year"] + 1)
    active_cycle = get_active_daewoon_cycle(daewoon, nominal_age)
    daewoon_ten_god = calculate_ten_god_for_stem(day_stem, active_cycle["stem"])
    year_rule = YEARLY_TEN_GOD_RULES[year_ten_god]
    daewoon_rule = YEARLY_TEN_GOD_RULES[daewoon_ten_god]
    advanced = _analysis_context_yearly_lines(analysis_context)
    headline = _pick_yearly_headline(
        year_ten_god=year_ten_god,
        daewoon_ten_god=daewoon_ten_god,
        target_year=target_year,
        saju_id=str(saju_result.get("saju_id", "")),
        analysis_context=analysis_context,
    )

    focus = _dedupe(year_rule["focus"] + daewoon_rule["focus"] + advanced["focus"])[:3]
    summary = _build_yearly_summary(
        year_rule=year_rule,
        daewoon_rule=daewoon_rule,
        year_ten_god=year_ten_god,
        daewoon_ten_god=daewoon_ten_god,
        target_year=target_year,
        saju_id=str(saju_result.get("saju_id", "")),
        focus=focus,
        advanced=advanced,
        analysis_context=analysis_context,
    )
    explanation = (
        f"{year_rule['explanation']} "
        f"여기에 현재 대운의 {daewoon_ten_god} 흐름이 겹쳐 {daewoon_rule['focus'][0]} 쪽 체감이 더 커질 수 있습니다."
    )
    advice = (
        f"{year_rule['advice']} "
        f"특히 올해는 {focus[0]}보다 앞서 {focus[1] if len(focus) > 1 else focus[0]}을 정리하는 편이 유리합니다."
    )
    if advanced["explanation"]:
        explanation = f"{explanation} {advanced['explanation']}"
    if advanced["advice"]:
        advice = f"{advice} {advanced['advice']}"
    section = build_yearly_section(
        headline=headline,
        explanation=explanation,
        advice=advice,
        focus=focus,
        seed=target_year + nominal_age,
    )
    section["one_line"] = headline
    section["headline"] = headline
    section["summary"] = headline

    return {
        "year": target_year,
        "pillar": year_pillar["kor"],
        "hanja": year_pillar["hanja"],
        "stem": year_pillar["stem"],
        "branch": year_pillar["branch"],
        "ten_god": year_ten_god,
        "daewoon_ten_god": daewoon_ten_god,
        "active_age": nominal_age,
        "active_daewoon": {
            "pillar": active_cycle["pillar"],
            "start_age": active_cycle["start_age"],
            "end_age": active_cycle["end_age"],
        },
        "headline": section["one_line"],
        "summary": summary,
        "explanation": " ".join(section["easy_explanation"]),
        "advice": " ".join(section["action_advice"]),
        "section": section,
        "focus": focus,
    }


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _analysis_context_yearly_lines(analysis_context: dict | None) -> dict:
    if not analysis_context:
        return {"summary": "", "explanation": "", "advice": "", "focus": []}

    strength = analysis_context["strength"]
    yongshin = analysis_context["yongshin"]
    flags = analysis_context["flags"]
    interactions = analysis_context["interactions"]

    summary = (
        f"중간 계산상 {strength['display_label']} 구조라 올해는 {yongshin['display']['primary']} 균형을 어떻게 쓰느냐가 체감 차이를 더 크게 만들 수 있습니다."
    )
    explanation = ""
    if interactions["with_yearly"]:
        item = interactions["with_yearly"][0]
        explanation = f"또한 세운과 원국은 {item['target']} {item['type']} 흐름이 걸려 {item['meaning']}"

    if flags["needs_resource_support"]:
        advice = f"올해는 {yongshin['display']['primary']}처럼 기반과 준비를 먼저 채우는 방향이 더 잘 맞습니다."
    elif flags["needs_output_release"]:
        advice = f"올해는 {yongshin['display']['primary']}처럼 결과를 밖으로 보이게 남기는 방향이 더 잘 맞습니다."
    else:
        advice = f"올해는 {yongshin['display']['primary']} 균형을 의식해 한쪽 과열을 먼저 줄이는 편이 좋습니다."

    focus: list[str] = []
    if flags.get("hidden_group_focus"):
        focus.append(flags["hidden_group_focus"])
    focus_map = {
        "metal": "정리",
        "water": "점검",
        "wood": "방향설정",
        "fire": "실행",
        "earth": "안정관리",
    }
    focus.append(focus_map[yongshin["primary_candidate"]])
    return {"summary": summary, "explanation": explanation, "advice": advice, "focus": focus}
