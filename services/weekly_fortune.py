"""Weekly fortune summary built from daily fortune scores."""

from __future__ import annotations

from datetime import date, timedelta

from services.daily_fortune import calculate_daily_fortune

WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


def build_weekly_fortune(saju_result: dict, start_date: date) -> list[dict]:
    """Return 7 compact daily summaries starting from ``start_date``."""
    weekly_items = []
    for offset in range(7):
        target_date = start_date + timedelta(days=offset)
        daily = calculate_daily_fortune(saju_result, target_date)
        score = daily["score"]
        weekly_items.append(
            {
                "date": target_date.isoformat(),
                "date_label": f"{target_date.month}/{target_date.day}",
                "weekday": WEEKDAY_LABELS[target_date.weekday()],
                "is_today": offset == 0,
                "score": score["value"],
                "grade": score["grade"],
                "label": score["label"],
                "summary": _build_short_summary(daily),
                "score_class": _score_class(score["value"]),
            }
        )
    return weekly_items


def _build_short_summary(daily: dict) -> str:
    score = daily["score"]["value"]
    keywords = set(daily.get("keywords", []))

    if score >= 80:
        if "기회" in keywords:
            return "기회 선별이 잘 맞음"
        if "성과" in keywords or "실행" in keywords:
            return "실행하면 성과가 남음"
        return "활용도가 높은 날"

    if score >= 65:
        if "정리" in keywords or "관리" in keywords:
            return "정리하면 흐름이 안정"
        if "신뢰" in keywords or "평가" in keywords:
            return "약속과 신뢰가 중요"
        return "움직임을 선별하면 좋음"

    if score >= 50:
        if "탐색" in keywords or "통찰" in keywords:
            return "탐색은 하되 보류"
        if "주의" in keywords or "분산" in keywords:
            return "무리보다 점검이 우선"
        return "관리 중심으로 운영"

    if score >= 35:
        if "긴장" in keywords or "압박" in keywords:
            return "속도보다 부담 조절"
        if "경쟁" in keywords:
            return "승부보다 한도 설정"
        return "확장보다 점검 필요"

    return "방어와 정리가 우선"


def _score_class(score: int) -> str:
    if score >= 80:
        return "score-high"
    if score >= 65:
        return "score-good"
    if score >= 50:
        return "score-normal"
    return "score-caution"
