"""Premium report builder for action-oriented paid insights."""

from __future__ import annotations

from services.interpretation_rules import build_seed

CORE_INSIGHT_TEMPLATES = [
    "이 사주는 속도보다 방향에서 결과가 갈립니다.",
    "문제는 기회가 아니라 선택 기준입니다.",
    "결과는 능력보다 운영 방식에서 차이가 납니다.",
    "이 구조는 확장보다 유지에서 강점이 드러납니다.",
    "지금은 움직이는 것보다 정리하는 것이 더 중요합니다.",
]

TIMING_TEMPLATES = [
    "지금 1~2년은 방향 설정 구간입니다.",
    "이 시기는 결과보다 기준을 만드는 시기입니다.",
    "지금 선택이 이후 10년 흐름을 좌우할 가능성이 큽니다.",
    "지금은 속도보다 구조를 잡는 시기입니다.",
    "이 구간에서는 빠른 확정보다 검토가 더 중요합니다.",
]

DECISION_COMPARE_TEMPLATES = [
    "확장 선택 시 기회는 늘지만 리스크도 함께 커집니다.",
    "유지 선택 시 속도는 줄지만 안정성은 높아집니다.",
    "지금은 선택보다 기준을 먼저 세우는 편이 더 유리합니다.",
    "둘 다 가능하지만 결과 차이는 운영 방식에서 갈립니다.",
    "선택 자체보다 선택 이후 관리가 더 중요한 구조입니다.",
]

PREMIUM_RISK_TEMPLATES = [
    "리스크는 상황이 아니라 선택 방식에서 발생합니다.",
    "기회가 많을수록 오히려 분산 위험이 커질 수 있습니다.",
    "감정이 앞서면 속도가 빨라지고 판단이 약해질 수 있습니다.",
    "기준이 없으면 좋은 기회도 결과로 이어지기 어렵습니다.",
    "문제는 외부가 아니라 내부 기준 부족일 가능성이 큽니다.",
]

ACTION_FORCE_TEMPLATES = [
    "반드시 하나는 줄이고, 하나는 유지하고, 하나는 정리해야 합니다.",
    "이번 달 안에 기준 하나를 숫자로 정해야 합니다.",
    "지금은 선택보다 정리가 먼저입니다.",
    "실행하지 않으면 이 해석은 의미가 없습니다.",
    "30일 안에 결과를 만들 수 있는 행동부터 시작해야 합니다.",
]


def build_premium_report(
    *,
    saju_result: dict,
    element_analysis: dict,
    ten_gods: dict,
    daewoon: dict,
    year_fortune: dict,
    career_fortune: dict,
    relationship_fortune: dict,
    interpretation: dict,
    premium_enabled: bool,
) -> dict:
    """Build premium-only report sections and teaser metadata."""
    seed = build_seed(
        saju_result["saju"]["year"]["kor"],
        saju_result["saju"]["month"]["kor"],
        saju_result["saju"]["day"]["kor"],
        saju_result["raw_input"]["target_year"],
    )
    dominant = ", ".join(element_analysis["dominant_kor"])
    weak = ", ".join(element_analysis["weak_kor"])
    active_cycle = daewoon["active_cycle_summary"]
    timeline_cycles = daewoon["cycles"][:3]
    current_decision_line = _pick(DECISION_COMPARE_TEMPLATES, seed + 3)
    current_core_line = _pick(CORE_INSIGHT_TEMPLATES, seed + 5)
    current_timing_line = _pick(TIMING_TEMPLATES, seed + 7)
    current_risk_line = _pick(PREMIUM_RISK_TEMPLATES, seed + 11)
    current_action_force = _pick(ACTION_FORCE_TEMPLATES, seed + 13)

    sections = [
        {
            "key": "timeline",
            "title": "인생 흐름 타임라인",
            "headline": "지금은 하나의 흐름만 볼 때가 아니라, 다음 흐름까지 함께 봐야 하는 구간입니다.",
            "summary_lines": [
                f"현재 대운은 {active_cycle['pillar']}이며, {active_cycle['ten_god']} 성향이 선택 부담과 경쟁 이슈를 함께 끌어올리고 있습니다.",
                f"이후 흐름은 {timeline_cycles[1]['pillar']}에서 구조 재정비와 방향 확정, {timeline_cycles[2]['pillar']}에서 결과 확정과 자리 안정으로 이어질 가능성이 큽니다.",
                current_timing_line,
            ],
            "patterns": [
                "지금은 결과를 크게 만들기보다 방향을 틀리지 않는 것이 더 중요합니다.",
                "현재 3년은 방향 설정 구간, 이후 10년은 결과 확정 구간으로 보는 편이 좋습니다.",
            ],
            "strength": "긴 호흡으로 흐름을 읽고 준비를 나눠 가져갈 수 있다는 점이 강점입니다.",
            "risk": "지금 당장 결과를 만들려는 조급함이 들어오면 다음 흐름 준비가 느슨해질 수 있습니다.",
            "core_insight": current_timing_line,
            "action_points": [
                "큰 결정은 준비, 실행, 확정 단계로 나눠서 접근합니다.",
                "지금 3년 안에 방향과 기준을 먼저 고정합니다.",
            ],
            "action_note": "지금은 성과보다 방향을 틀리지 않는 쪽이 더 중요합니다.",
        },
        {
            "key": "decision_points",
            "title": "인생 결정 포인트 분석",
            "headline": "이 구조에서는 감정보다 유지 가능성이 더 중요한 기준이 됩니다.",
            "summary_lines": [
                f"강한 오행은 {dominant}, 약한 오행은 {weak}이라 판단할 때 장기 유지와 리스크 관리가 같이 들어옵니다.",
                f"월간 십성 {ten_gods['ten_gods']['month']}은 {ten_gods['ten_gods_explanations']['month']}",
                "좋은 선택보다 남는 선택에서 결과 차이가 벌어지는 구조입니다.",
            ],
            "patterns": [
                "기회가 와도 바로 움직이지 않고 조건을 먼저 따져보는 편입니다.",
                "감정보다 구조를 먼저 고려하고, 한 번 결정하면 오래 유지하는 경향이 있습니다.",
                interpretation["interpretation_sections"]["overall"]["highlight"],
            ],
            "strength": "기준이 있어 큰 실수를 줄이는 구조입니다.",
            "risk": "판단 시간이 길어지면 타이밍을 놓칠 수 있습니다.",
            "core_insight": current_core_line if "선택 기준" in current_core_line else "문제는 기회가 아니라 선택 기준입니다.",
            "action_points": [
                "모든 큰 결정은 계속 유지 가능한지를 기준으로 판단합니다.",
                current_decision_line,
            ],
            "action_note": "결정은 빠른 승부보다 조건 검증형으로 가져가는 편이 좋습니다.",
        },
        {
            "key": "wealth_deep",
            "title": "재물 흐름 심층 분석",
            "headline": "이 사주의 재물은 얼마나 버느냐보다 얼마나 남기느냐에서 차이가 납니다.",
            "summary_lines": [
                f"올해 재물 기조는 '{saju_result['summary_card']['wealth']}'이고, 세운에서는 {year_fortune['ten_god']} 흐름이 재물 판단에 영향을 줍니다.",
                "지금은 확장보다 축적과 관리에 더 무게가 실립니다.",
                interpretation["interpretation_sections"]["wealth"]["highlight"],
            ],
            "patterns": [
                "수입 규모보다 지출 구조가 결과를 좌우합니다.",
                "기준이 없으면 흐름이 쉽게 흔들리지만, 관리 체계가 잡히면 빠르게 안정됩니다.",
                "돈은 감각보다 반복 관리에서 실력이 드러나는 편입니다.",
            ],
            "strength": "꾸준히 쌓는 구조에서 강점을 보입니다.",
            "risk": "확장 타이밍이 늦어지면 기회 활용 속도가 떨어질 수 있습니다.",
            "core_insight": "돈은 속도가 아니라 구조에서 남습니다.",
            "action_points": [
                "고정비 점검 기준을 먼저 세웁니다.",
                "계좌를 분리하고 월 단위 현금 흐름을 체크합니다.",
                current_action_force,
            ],
            "action_note": "재물은 벌기보다 남기는 체계에서 결과가 갈립니다.",
        },
        {
            "key": "career_direction",
            "title": "직업 / 사업 방향 분석",
            "headline": "이 구조는 빠른 성과형보다 관리와 누적형에서 더 강합니다.",
            "summary_lines": [
                f"현재 직장운은 '{career_fortune['headline']}'로 읽히며, 지금은 성과보다 운영 능력이 더 중요하게 작동합니다.",
                f"세운/대운 십성은 {year_fortune['ten_god']} / {year_fortune['daewoon_ten_god']}로, 역할과 운영 기준을 동시에 시험하는 구간입니다.",
                career_fortune["section"]["highlight"],
            ],
            "patterns": [
                "역할이 명확할수록 강점이 더 잘 드러납니다.",
                "관리와 실적이 같이 필요하고, 선택이 많아질수록 분산 위험이 커집니다.",
                "사업으로 넓히더라도 수익 구조를 먼저 확인한 뒤 확장하는 편이 좋습니다.",
            ],
            "strength": "지속 가능한 구조에서 성과를 유지하는 힘이 있습니다.",
            "risk": "기회가 많을수록 우선순위가 흐려져 분산이 생길 수 있습니다.",
            "core_insight": "성과는 능력보다 운영 방식에서 갈립니다.",
            "action_points": [
                "직장에서는 평가 기준을 눈에 보이게 정리합니다.",
                "사업은 수익 구조를 먼저 검증한 뒤 확장합니다.",
            ],
            "action_note": "지금은 성과보다 운영 기준을 세우는 편이 더 중요합니다.",
        },
        {
            "key": "relationship_deep",
            "title": "관계 심층 분석",
            "headline": "이 구조에서는 감정보다 관계의 속도와 리듬이 더 중요합니다.",
            "summary_lines": [
                relationship_fortune["summary"],
                "관계가 틀어지는 이유는 감정보다 타이밍 문제인 경우가 더 많습니다.",
                relationship_fortune["section"]["highlight"],
            ],
            "patterns": [
                "관계 시작은 느릴 수 있지만, 깊어지면 오래 유지하는 편입니다.",
                "감정 표현은 늦을 수 있어 타이밍이 어긋날 가능성을 같이 봐야 합니다.",
                "좋아도 빨리 확정하기보다 서로의 생활 리듬과 현실 조건을 함께 보는 편이 좋습니다.",
            ],
            "strength": "신뢰 기반 관계를 오래 유지하는 힘이 있습니다.",
            "risk": "타이밍이 어긋나면 감정보다 거리감 문제로 관계가 흔들릴 수 있습니다.",
            "core_insight": "관계는 감정이 아니라 속도에서 갈립니다.",
            "action_points": [
                "관계 속도를 조절합니다.",
                "현실 조건을 함께 확인합니다.",
                "결론을 서두르지 않습니다.",
            ],
            "action_note": "관계는 감정보다 리듬이 맞을 때 더 오래 갑니다.",
        },
        {
            "key": "risk_analysis",
            "title": "리스크 분석",
            "headline": "이 사주의 리스크는 운이 아니라 선택 구조에서 발생합니다.",
            "summary_lines": [
                f"특히 약한 오행 {weak}이 흔들릴 때 방향 흔들림과 분산이 같이 나타날 수 있습니다.",
                current_risk_line,
                "문제는 외부 충격보다 내부 기준이 약해질 때 더 크게 커집니다.",
            ],
            "patterns": [
                "선택 기준이 흔들리면 좋은 기회도 쉽게 분산됩니다.",
                "기회가 많아질수록 오히려 무엇을 버릴지 정하지 못해 피로가 커질 수 있습니다.",
                "감정이 앞서 결정하면 속도는 빨라지지만 유지력이 약해질 수 있습니다.",
            ],
            "strength": "한 번 기준을 잡으면 리스크를 빠르게 줄이는 편입니다.",
            "risk": "기준 없이 움직이면 분산과 결정 피로가 동시에 올라올 수 있습니다.",
            "core_insight": "리스크는 상황이 아니라 선택 방식에서 발생합니다.",
            "action_points": [
                "일정 상한선을 정합니다.",
                "지출 상한선을 정합니다.",
                "관계 거리 기준을 정합니다.",
            ],
            "action_note": "리스크는 감으로 다루지 말고 숫자와 선으로 관리해야 합니다.",
        },
        {
            "key": "action_plan",
            "title": "실행 전략 (Action Plan)",
            "headline": "이 리포트의 핵심은 이해가 아니라 실행입니다.",
            "summary_lines": [
                "결과는 설명을 많이 읽는다고 바뀌지 않습니다.",
                "이번 해석은 당장 30일 안에 옮길 수 있는 행동으로 바꿔야 의미가 생깁니다.",
                _pick(ACTION_FORCE_TEMPLATES, seed + 17),
            ],
            "patterns": [
                "1단계 이번 달: 줄일 지출 1개, 정리할 일 1개, 확인할 관계 1개를 고릅니다.",
                "2단계 올해: 유지할 것과 바꿀 것을 구분하고 우선순위 3개를 세웁니다.",
                "3단계 다음 흐름 준비: 자금, 경험, 방향 세 축을 먼저 준비합니다.",
            ],
            "strength": "실행 순서를 잘 나누면 작은 행동도 실제 결과로 빠르게 이어질 수 있습니다.",
            "risk": "좋은 해석을 이해만 하고 행동으로 옮기지 않으면 체감 변화는 거의 남지 않습니다.",
            "core_insight": "결과는 이해가 아니라 실행에서 바뀝니다.",
            "action_points": [
                "이번 달 안에 기준 하나를 숫자로 정합니다.",
                "30일 단위 실행표로 옮깁니다.",
                "하나는 줄이고, 하나는 유지하고, 하나는 정리합니다.",
            ],
            "action_note": "실행하지 않으면 이 해석은 의미가 없습니다.",
        },
    ]
    teaser_items = [{"title": section["title"], "teaser": section["core_insight"]} for section in sections[:4]]
    return {
        "enabled": premium_enabled,
        "tier": "premium" if premium_enabled else "free-preview",
        "header": "프리미엄 사주 리포트",
        "intro": "이 리포트는 단순한 성향 설명이 아니라, 앞으로 어떤 선택을 해야 하는지까지 정리한 실행형 분석입니다.",
        "overview": [
            "현재 구조는 안정과 판단이 먼저 작동하는 흐름 위에, 외부 변화와 기회가 동시에 들어오는 상태입니다.",
            "그래서 무리하게 확장하기보다 선택 기준을 먼저 세우는 것이 결과를 좌우합니다.",
            _pick(CORE_INSIGHT_TEMPLATES, seed + 19),
        ],
        "final_summary": {
            "headline": "최종 정리",
            "text": "이 사주는 빠르게 움직일수록 유리한 구조가 아니라, 정확하게 선택할수록 결과가 좋아지는 구조입니다. 지금 중요한 건 더 많은 기회가 아니라 더 명확한 기준입니다.",
        },
        "cta_title": "프리미엄 리포트로 결정 포인트까지 확인하기",
        "cta_description": "인생 타임라인, 리스크, 실행 전략까지 묶어 실제 선택에 쓰는 정보로 확장합니다.",
        "teaser_items": teaser_items,
        "sections": sections,
    }


def _pick(options: list[str], seed: int) -> str:
    return options[seed % len(options)]
