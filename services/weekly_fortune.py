"""Weekly fortune summary built from daily fortune scores."""

from __future__ import annotations

from datetime import date, timedelta

from services.analysis_context import build_analysis_context
from services.daewoon import calculate_daewoon
from services.daily_fortune import calculate_daily_fortune
from services.element_analyzer import analyze_elements
from services.ten_gods import calculate_ten_gods
from services.yearly_fortune import calculate_yearly_fortune

WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]

SHORT_SUMMARY_POOLS = {
    "very_high": [
        "오늘은 강하게 활용",
        "핵심 기회가 선명함",
        "큰일 처리에 유리",
        "성과 흐름이 강함",
        "중요 결정에 힘이 붙음",
        "활용도가 매우 높음",
        "주도하면 결과가 큼",
        "기회가 또렷한 날",
        "실행 탄력이 강함",
        "성과 회수에 좋은 날",
        "확정과 마감에 유리",
        "흐름을 잡기 좋음",
        "추진해도 무리 적음",
        "중요 접점이 살아남",
        "집중하면 크게 남음",
        "기준 잡고 밀어도 좋음",
        "오늘은 적극 승부",
        "실행 가치가 큰 날",
        "좋은 흐름을 잡기",
        "결과를 만들기 좋음",
        "선택 집중이 강함",
        "계획 실행에 최상",
        "성과와 신뢰가 동반",
        "오늘은 기회 활용",
    ],
    "high": [
        "실행하면 성과가 남음",
        "기회 선별이 잘 맞음",
        "활용도가 높은 날",
        "마감과 제안에 유리",
        "움직이면 결과가 남음",
        "중요한 일 처리 좋음",
        "정리 뒤 실행이 유리",
        "대외 접점이 살아남",
        "선택 집중이 잘 맞음",
        "성과 확인에 좋은 날",
        "약속이 신뢰로 남음",
        "결정하면 힘이 붙음",
        "능동 대응이 유리함",
        "실무 성과가 또렷함",
        "좋은 접점이 생김",
        "준비한 일이 풀림",
        "우선순위가 잘 맞음",
        "작은 실행도 남음",
        "협업에서 성과 남음",
        "계획 실행에 강함",
        "정리와 성과가 연결",
        "잡을 기회가 보임",
        "신뢰 확보에 좋음",
        "오늘은 적극 활용",
    ],
    "good": [
        "정리하면 흐름 안정",
        "약속과 신뢰가 중요",
        "움직임 선별이 좋음",
        "무난하게 쓰기 좋음",
        "관리하면 결과가 남음",
        "선택 기준이 중요함",
        "작은 실행이 유리함",
        "일정 조율이 잘 맞음",
        "필요한 일부터 처리",
        "관계 조율에 적합",
        "돈 흐름 점검 좋음",
        "마감 정리에 유리",
        "속도보다 균형 우선",
        "조건 확인이 유리함",
        "가볍게 추진해도 좋음",
        "협의 후 움직이면 좋음",
        "정돈하면 체감 좋음",
        "일상 관리에 유리",
        "쌓는 흐름이 안정",
        "선별 대응이 맞음",
        "준비한 일 진행 좋음",
        "안정적 운영 가능",
        "확정보다 점검 먼저",
        "해야 할 일 처리 좋음",
    ],
    "normal": [
        "관리 중심으로 운영",
        "무리보다 점검 우선",
        "탐색은 하되 보류",
        "큰 변화는 천천히",
        "정리하면 무난한 날",
        "속도보다 확인 필요",
        "작은 일부터 마감",
        "판단은 한 박자 늦게",
        "새 일보다 기존 정리",
        "관계 속도 조절 필요",
        "지출 기준을 확인",
        "무난하나 분산 주의",
        "우선순위만 지키기",
        "확장보다 유지 우선",
        "오늘은 균형이 핵심",
        "일정 과밀은 피하기",
        "말보다 확인이 중요",
        "한 가지에 집중하기",
        "감정보다 기준 우선",
        "바로 결정은 보류",
        "작게 움직이면 안정",
        "기본 루틴을 지키기",
        "변수는 작게 다루기",
        "점검 후 움직이기",
    ],
    "caution": [
        "속도보다 부담 조절",
        "승부보다 한도 설정",
        "확장보다 점검 필요",
        "감정 반응을 줄이기",
        "무리한 약속은 피함",
        "지출 확대는 보류",
        "말의 강약을 낮추기",
        "오늘은 확인이 우선",
        "충동 결정은 피하기",
        "일정 줄이는 게 좋음",
        "관계 마찰을 조심",
        "과속보다 정지가 낫다",
        "큰 결정은 늦추기",
        "압박은 나눠서 처리",
        "피로 신호를 보기",
        "경쟁심은 낮추기",
        "조건표 먼저 만들기",
        "잡을 일만 남기기",
        "분산을 줄여야 함",
        "말보다 기록이 안전",
        "새 제안은 검토만",
        "반응보다 정리 우선",
        "한도를 먼저 정하기",
        "몸과 일정 보호하기",
    ],
    "defense": [
        "방어와 정리가 우선",
        "확대보다 보류가 좋음",
        "오늘은 무리 금물",
        "큰 결정은 피하기",
        "일정부터 줄이기",
        "지출은 최소로 관리",
        "관계 거리를 두기",
        "충돌은 피하는 날",
        "체력 회복이 우선",
        "새 약속은 미루기",
        "정리만 해도 충분",
        "손실 방지가 핵심",
        "말수 줄이면 안전",
        "방향 재점검 필요",
        "속도보다 멈춤 필요",
        "무리한 승부는 보류",
        "오늘은 버티는 날",
        "작게 닫는 게 좋음",
        "외부 자극 줄이기",
        "한 가지도 충분함",
        "기준 밖 일은 보류",
        "감정 소모를 줄이기",
        "휴식도 전략이 됨",
        "안전한 선택이 우선",
    ],
}

REASON_TAG_SHORT_POOLS = {
    "용신 정합": [
        "원국 결이 잘 받는 날",
        "균형과 잘 맞는 날",
        "용신 정합도가 높음",
        "체감 활용도가 잘 붙음",
        "균형 회복이 쉬운 날",
        "내 결에 잘 맞는 날",
    ],
    "균형 회복": [
        "균형 회복에 유리함",
        "정리와 회복이 맞음",
        "무리보다 회복 유리",
        "안정감 회복이 좋음",
        "기준 복구에 좋은 날",
        "흐름 재정비에 적합",
    ],
    "실행 기회": [
        "실행력이 붙는 날",
        "움직이면 남는 날",
        "성과 연결이 쉬움",
        "실행 타이밍이 좋음",
        "결과 만들기 좋음",
        "작은 실행도 남음",
    ],
    "재물 흐름": [
        "돈 기준 세우기 좋음",
        "재물 판단이 또렷함",
        "관리 기준이 잘 맞음",
        "실무와 돈 점검 유리",
        "축적 감각이 살아남",
        "재정 정리가 잘 맞음",
    ],
    "관계 조율": [
        "관계 조율이 중요함",
        "사람 흐름 읽기 좋음",
        "속도 조절이 잘 맞음",
        "관계 리듬 점검 유리",
        "대화 조율이 중요함",
        "거리 조절이 핵심임",
    ],
    "정리 우선": [
        "정리 순서가 중요함",
        "기준부터 세우기 좋음",
        "할 일 정돈이 잘 맞음",
        "우선순위 정리가 핵심",
        "정리 중심 운영이 유리",
        "기준 잡고 가기 좋음",
    ],
    "속도 조절": [
        "속도 조절이 핵심임",
        "반응 수위를 낮추기",
        "서두름 조절이 중요함",
        "빠름보다 완성도 우선",
        "한 박자 늦추면 좋음",
        "과속만 줄이면 괜찮음",
    ],
    "변동 관리": [
        "변수 관리가 중요함",
        "흐름 변동 점검 유리",
        "작은 변화 관리 필요",
        "범위 조절이 잘 맞음",
        "변수만 줄이면 안정",
        "움직임 관리가 핵심임",
    ],
    "변동 주의": [
        "작은 변동 관리 필요",
        "일정 흔들림을 조심",
        "변수 확장은 피하기",
        "틈새 리스크 점검",
        "미세 변동에 주의",
        "가벼운 흔들림을 보기",
    ],
    "리듬 주의": [
        "생활 리듬 점검 필요",
        "속도 간격을 맞추기",
        "리듬 흔들림을 조심",
        "페이스 조절이 중요함",
        "휴식 간격을 챙기기",
        "흐름 리듬을 보기",
    ],
    "압력 주의": [
        "압박 강도 조절 필요",
        "부담 한도를 정하기",
        "압력 대응이 핵심임",
        "무리한 버팀은 피하기",
        "기준 범위 축소 필요",
        "압박 관리가 우선임",
    ],
    "충돌 주의": [
        "충돌 신호를 조심",
        "마찰 가능성 점검",
        "속도 조절이 필요함",
        "강한 반응은 주의",
        "무리수는 피해야 함",
        "충돌 관리가 중요함",
    ],
    "운 압박": [
        "압박 대응이 중요함",
        "부담 조절이 우선",
        "운 압력 관리 필요",
        "한도 설정이 중요함",
        "무리 줄이기 우선",
        "피로 관리가 핵심임",
    ],
    "방어 우선": [
        "방어 운영이 우선",
        "손실 줄이기 중요",
        "확장보다 보호가 맞음",
        "보수적 선택이 유리",
        "일정 줄이기 우선",
        "방어 집중이 맞음",
    ],
}

REASON_CAUTION_SHORT_POOLS = {
    ("용신 정합", "리듬 주의"): [
        "좋은 흐름, 리듬 점검",
        "기회+페이스 관리",
        "활용하되 속도 점검",
    ],
    ("실행 기회", "충돌 주의"): [
        "기회는 크나 충돌 주의",
        "실행 전 마찰 점검",
        "성과보다 조율 먼저",
    ],
    ("재물 흐름", "변동 주의"): [
        "돈 흐름, 변동 점검",
        "실속은 좋고 변수 주의",
        "선별 소비가 유리함",
    ],
    ("관계 조율", "압력 주의"): [
        "관계 조율+압박 관리",
        "대화는 좋고 부담 주의",
        "연결은 되나 속도 조절",
    ],
    ("정리 우선", "충돌 주의"): [
        "정리 우선, 마찰 조심",
        "기준 유지가 핵심",
        "속도보다 정돈이 유리",
    ],
}


def calculate_daily_fortune_for_weekly(
    saju_result: dict,
    target_date: date,
    *,
    element_analysis: dict,
    ten_gods: dict,
    daewoon: dict | None = None,
    year_fortune: dict | None = None,
) -> dict:
    """Compute daily fortune with the same context path used by weekly cards."""
    base_daily = calculate_daily_fortune(saju_result, target_date)
    analysis_context = build_analysis_context(
        saju_result=saju_result,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        daily_fortune=base_daily,
    )
    return calculate_daily_fortune(saju_result, target_date, analysis_context=analysis_context)


def build_weekly_fortune(
    saju_result: dict,
    start_date: date,
    *,
    gender: str | None = None,
    daewoon: dict | None = None,
) -> list[dict]:
    """Return 7 compact daily summaries starting from ``start_date``."""
    element_analysis = analyze_elements(saju_result["saju"])
    ten_gods = calculate_ten_gods(saju_result["saju"])
    resolved_gender = gender or saju_result.get("raw_input", {}).get("gender")
    resolved_daewoon = daewoon
    if resolved_daewoon is None and resolved_gender in {"male", "female"}:
        resolved_daewoon = calculate_daewoon(saju_result, gender=resolved_gender)
    yearly_cache: dict[int, dict | None] = {}
    weekly_items = []
    used_summaries: set[str] = set()
    used_drivers: set[str] = set()
    for offset in range(7):
        target_date = start_date + timedelta(days=offset)
        year_fortune = None
        if resolved_daewoon:
            year_fortune = yearly_cache.get(target_date.year)
            if year_fortune is None:
                year_fortune = calculate_yearly_fortune(saju_result, resolved_daewoon, target_date.year)
                yearly_cache[target_date.year] = year_fortune
        daily = calculate_daily_fortune_for_weekly(
            saju_result,
            target_date,
            element_analysis=element_analysis,
            ten_gods=ten_gods,
            daewoon=resolved_daewoon,
            year_fortune=year_fortune,
        )
        score = daily["score"]
        summary = _build_short_summary(daily, target_date, used_summaries=used_summaries)
        driver_line = _build_weekly_driver_line(score, target_date, used_drivers=used_drivers)
        weekly_items.append(
            {
                "date": target_date.isoformat(),
                "date_label": f"{target_date.month}/{target_date.day}",
                "weekday": WEEKDAY_LABELS[target_date.weekday()],
                "is_today": offset == 0,
                "score": score["value"],
                "grade": score["grade"],
                "label": score["label"],
                "reason_tag": score.get("reason_tag"),
                "caution_tag": score.get("caution_tag"),
                "confidence": score.get("confidence", "high"),
                "confidence_label": _confidence_label(score.get("confidence", "high")),
                "driver_line": driver_line,
                "factor_top": (score.get("factor_highlights") or [None])[0],
                "factor_top_compact": _compact_factor_line((score.get("factor_highlights") or [None])[0] or ""),
                "summary": summary,
                "score_class": _score_class(score["value"]),
            }
        )
    return weekly_items


def _build_short_summary(daily: dict, target_date: date, *, used_summaries: set[str] | None = None) -> str:
    score = daily["score"]["value"]
    bucket = _summary_bucket(score)
    reason_tag = daily["score"].get("reason_tag")
    caution_tag = daily["score"].get("caution_tag")
    confidence = daily["score"].get("confidence", "high")
    options = (
        REASON_CAUTION_SHORT_POOLS.get((reason_tag, caution_tag))
        or REASON_TAG_SHORT_POOLS.get(reason_tag)
        or SHORT_SUMMARY_POOLS[bucket]
    )
    keyword_seed = sum(sum(ord(char) for char in keyword) for keyword in daily.get("keywords", []))
    confidence_seed = {"high": 1, "medium": 2, "low": 3}.get(confidence, 0)
    caution_seed = sum(ord(char) for char in str(caution_tag or ""))
    base_index = (target_date.toordinal() + score + keyword_seed + confidence_seed + caution_seed) % len(options)

    if not used_summaries:
        return options[base_index]

    for offset in range(len(options)):
        candidate = options[(base_index + offset) % len(options)]
        if candidate not in used_summaries:
            used_summaries.add(candidate)
            return candidate

    candidate = options[base_index]
    used_summaries.add(candidate)
    return candidate


def _summary_bucket(score: int) -> str:
    if score >= 90:
        return "very_high"
    if score >= 80:
        return "high"
    if score >= 65:
        return "good"
    if score >= 50:
        return "normal"
    if score >= 35:
        return "caution"
    return "defense"


def _score_class(score: int) -> str:
    if score >= 90:
        return "score-very-high"
    if score >= 80:
        return "score-high"
    if score >= 65:
        return "score-good"
    if score >= 50:
        return "score-normal"
    return "score-caution"


def _confidence_label(confidence: str) -> str:
    labels = {
        "high": "확신 높음",
        "medium": "확신 중간",
        "low": "보수 해석",
    }
    return labels.get(confidence, "확신 중간")


def _build_weekly_driver_line(score: dict, target_date: date, *, used_drivers: set[str] | None = None) -> str | None:
    options: list[str] = []
    base_driver = score.get("driver_line")
    if base_driver:
        options.append(base_driver)

    for factor in score.get("factor_highlights") or []:
        compact = _compact_factor_line(factor)
        if compact:
            options.append(compact)

    reason_tag = score.get("reason_tag")
    caution_tag = score.get("caution_tag")
    if reason_tag and caution_tag:
        options.append(f"{reason_tag} 중심, {caution_tag}는 점검")
    elif reason_tag:
        options.append(f"{reason_tag} 중심으로 운영")

    if not options:
        return None

    seed = target_date.toordinal() + int(score.get("value", 0))
    base_index = seed % len(options)

    if not used_drivers:
        return options[base_index]

    for offset in range(len(options)):
        candidate = options[(base_index + offset) % len(options)]
        if candidate not in used_drivers:
            used_drivers.add(candidate)
            return candidate

    candidate = options[base_index]
    used_drivers.add(candidate)
    return candidate


def _compact_factor_line(factor_line: str) -> str:
    if not factor_line:
        return ""
    if "·" in factor_line:
        return factor_line.split("·", 1)[0].strip()
    return factor_line.strip()
