"""FastAPI entrypoint for the saju MVP."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import logging
import os
import re
import time
from urllib.parse import urlencode

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment]

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional runtime helper
    def load_dotenv() -> bool:
        return False
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.templating import Jinja2Templates

from services.career_fortune import build_career_fortune
from services.analysis_context import build_analysis_context
from services.daily_fortune import calculate_daily_fortune
from services.daewoon import calculate_daewoon
from services.element_analyzer import analyze_elements
from services.email_sender import send_report_email
from services.interpretation import build_interpretation
from services.lead_store import build_lead_payload, save_lead
from services.monthly_fortune import calculate_monthly_fortune
from services.pdf_generator import generate_pdf_bytes
from services.premium_report import build_premium_report
from services.report_builder import ReportBuilder, build_structured_report, clear_sentence_db_cache
from services.report_display import build_display_result
from services.relationship_fortune import build_relationship_fortune
from services.saju_calculator import (
    SajuCalculationError,
    get_basic_saju_result,
    get_time_slot_options,
)
from services.summary_card import build_summary_card
from services.ten_gods import calculate_ten_gods
from services.sentence_filter import SentenceFilter
from services.sentence_matcher import SentenceMatcher
from services.signal_extractor import extract_interpretation_signals
from services.structure_analyzer import StructureAnalyzer
from services.weekly_fortune import build_weekly_fortune, calculate_daily_fortune_for_weekly
from services.yearly_fortune import calculate_yearly_fortune

load_dotenv()

app = FastAPI(title="saju-mvp")
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EMAIL_REQUEST_LOG: dict[str, float] = {}
EMAIL_RATE_LIMIT_SECONDS = 60
ANALYSIS_CONTEXT_CACHE: dict[str, dict] = {}
ANALYSIS_CONTEXT_CACHE_MAX = 256

try:
    SEOUL_TZ = ZoneInfo("Asia/Seoul") if ZoneInfo else timezone(timedelta(hours=9))
except ZoneInfoNotFoundError:  # pragma: no cover - defensive timezone fallback
    SEOUL_TZ = timezone(timedelta(hours=9))


def _today_in_seoul() -> date:
    return datetime.now(SEOUL_TZ).date()


def _birth_year_options() -> list[int]:
    current_year = _today_in_seoul().year
    return list(range(current_year, 1899, -1))


def _month_options() -> list[int]:
    return list(range(1, 13))


def _day_options() -> list[int]:
    return list(range(1, 32))


def _build_index_context(
    *,
    form_data: dict | None = None,
    error_message: str | None = None,
    email_form_data: dict | None = None,
    email_error_message: str | None = None,
    email_success_message: str | None = None,
) -> dict:
    return {
        "form_data": form_data or _default_form_data(),
        "email_form_data": email_form_data or _default_email_form_data(),
        "error_message": error_message,
        "email_error_message": email_error_message,
        "email_success_message": email_success_message,
        "time_slots": get_time_slot_options(),
        "birth_year_options": _birth_year_options(),
        "month_options": _month_options(),
        "day_options": _day_options(),
    }


def _default_form_data() -> dict:
    today = _today_in_seoul()
    return {
        "calendar_type": "solar",
        "year": "",
        "month": "",
        "day": "",
        "time_slot": "",
        "is_leap_month": False,
        "gender": "",
        "target_year": str(today.year),
        "target_month": str(today.month),
        "target_date": today.isoformat(),
    }


def _default_email_form_data() -> dict:
    return {
        "email": "",
        "name": "",
        "consent": False,
    }


def _parse_optional_int(value: str | None, field_name: str) -> int | None:
    if value is None or value == "":
        return None

    try:
        return int(value)
    except ValueError as exc:
        raise SajuCalculationError(f"{field_name} 값은 숫자로 입력해 주세요.") from exc


def _parse_target_date(value: str | None) -> date:
    if value is None or value == "":
        return _today_in_seoul()

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SajuCalculationError("기준 날짜는 YYYY-MM-DD 형식으로 입력해 주세요.") from exc


def _validate_gender(gender: str | None) -> str:
    if gender not in {"male", "female"}:
        raise SajuCalculationError("성별은 필수로 선택해 주세요.")
    return gender


def _validate_email(email: str | None) -> str:
    if not email:
        raise SajuCalculationError("이메일은 필수로 입력해 주세요.")
    normalized = email.strip().lower()
    if not EMAIL_RE.match(normalized):
        raise SajuCalculationError("올바른 이메일 형식이 아닙니다.")
    return normalized


def _check_email_rate_limit(email: str, birth_signature: str) -> None:
    key = f"{email}:{birth_signature}"
    now = time.monotonic()
    last = EMAIL_REQUEST_LOG.get(key)
    if last and now - last < EMAIL_RATE_LIMIT_SECONDS:
        raise SajuCalculationError("잠시 후 다시 시도해 주세요. 같은 리포트 요청이 너무 빠르게 반복되었습니다.")


def _mark_email_rate_limit(email: str, birth_signature: str) -> None:
    EMAIL_REQUEST_LOG[f"{email}:{birth_signature}"] = time.monotonic()


def _build_birth_signature(form_data: dict) -> str:
    return "|".join(
        str(form_data.get(key, ""))
        for key in ["calendar_type", "year", "month", "day", "time_slot", "gender", "target_year", "target_date"]
    )


def _build_report_view_link(request: Request, result_data: dict) -> str:
    query = urlencode(_build_report_query_params(result_data))
    return f"{request.base_url}report/view?{query}"


def _build_premium_upgrade_link(request: Request, result_data: dict) -> str:
    query = urlencode(_build_report_query_params(result_data, premium=True))
    return f"{request.base_url}report/view?{query}"


def _build_premium_pdf_link(request: Request, result_data: dict) -> str:
    query = urlencode(_build_report_query_params(result_data, premium=True))
    return f"{request.base_url}report/pdf?{query}"


def _build_report_query_params(result_data: dict, premium: bool = False) -> dict:
    return {
        "calendar_type": result_data["raw_input"]["calendar_type"],
        "year": result_data["raw_input"]["year"],
        "month": result_data["raw_input"]["month"],
        "day": result_data["raw_input"]["day"],
        "time_slot": result_data["raw_input"].get("time_slot") or "",
        "is_leap_month": "1" if result_data["raw_input"]["is_leap_month"] else "0",
        "gender": result_data["raw_input"]["gender"],
        "target_year": result_data["raw_input"]["target_year"],
        "target_month": result_data["raw_input"]["target_month"] or "",
        "target_date": result_data["raw_input"]["target_date"],
        "premium": "1" if premium else "0",
    }


def _build_analysis_context_cache_key(
    *,
    saju_id: str,
    gender: str,
    target_year: int,
    target_month: int | None,
    target_date: date,
) -> str:
    return "|".join(
        [
            saju_id,
            gender,
            str(target_year),
            str(target_month or 0),
            target_date.isoformat(),
        ]
    )


def _get_cached_analysis_context(cache_key: str) -> dict | None:
    cached = ANALYSIS_CONTEXT_CACHE.get(cache_key)
    if cached is None:
        return None
    return deepcopy(cached)


def _set_cached_analysis_context(cache_key: str, context: dict) -> None:
    if len(ANALYSIS_CONTEXT_CACHE) >= ANALYSIS_CONTEXT_CACHE_MAX and cache_key not in ANALYSIS_CONTEXT_CACHE:
        oldest_key = next(iter(ANALYSIS_CONTEXT_CACHE))
        ANALYSIS_CONTEXT_CACHE.pop(oldest_key, None)
    ANALYSIS_CONTEXT_CACHE[cache_key] = deepcopy(context)


def _is_checked(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return value in {"on", "1", "true", "True"}


def _build_result_data(
    calendar_type: str,
    year: int,
    month: int,
    day: int,
    time_slot: str | None,
    is_leap_month: str | bool | None,
    gender: str | None,
    target_year: str | None,
    target_month: str | None,
    target_date: str | None,
    premium: str | bool | None = None,
) -> tuple[dict, dict]:
    form_data = {
        "calendar_type": calendar_type,
        "year": year,
        "month": month,
        "day": day,
        "time_slot": time_slot or "",
        "is_leap_month": _is_checked(is_leap_month),
        "gender": gender,
        "target_year": target_year or str(_today_in_seoul().year),
        "target_month": target_month or str(_today_in_seoul().month),
        "target_date": target_date or _today_in_seoul().isoformat(),
        "premium": _is_checked(premium),
    }

    parsed_target_year = _parse_optional_int(target_year, "기준 연도") or _today_in_seoul().year
    parsed_target_month = _parse_optional_int(target_month, "기준 월")
    parsed_target_date = _parse_target_date(target_date)

    gender = _validate_gender(gender)
    if parsed_target_month is not None and not 1 <= parsed_target_month <= 12:
        raise SajuCalculationError("기준 월은 1부터 12 사이여야 합니다.")

    result_data = get_basic_saju_result(
        calendar_type=calendar_type,
        year=year,
        month=month,
        day=day,
        time_slot=time_slot or None,
        is_leap_month=_is_checked(is_leap_month),
    )
    analysis_context_cache_key = _build_analysis_context_cache_key(
        saju_id=result_data["saju_id"],
        gender=gender,
        target_year=parsed_target_year,
        target_month=parsed_target_month,
        target_date=parsed_target_date,
    )

    element_analysis = analyze_elements(result_data["saju"])
    ten_gods = calculate_ten_gods(result_data["saju"])
    daewoon = calculate_daewoon(result_data, gender=gender)
    year_fortune = calculate_yearly_fortune(result_data, daewoon, parsed_target_year)
    daily_fortune = calculate_daily_fortune(result_data, parsed_target_date)
    analysis_context = _get_cached_analysis_context(analysis_context_cache_key)
    if analysis_context is None:
        analysis_context = build_analysis_context(
            saju_result=result_data,
            element_analysis=element_analysis,
            ten_gods=ten_gods,
            daewoon=daewoon,
            year_fortune=year_fortune,
            daily_fortune=daily_fortune,
        )
        _set_cached_analysis_context(analysis_context_cache_key, analysis_context)
    interpretation_signals = extract_interpretation_signals(analysis_context)
    structured_report = build_structured_report(analysis_context, interpretation_signals)
    daily_fortune = calculate_daily_fortune(result_data, parsed_target_date, analysis_context=analysis_context)
    year_fortune = calculate_yearly_fortune(
        result_data,
        daewoon,
        parsed_target_year,
        analysis_context=analysis_context,
    )
    monthly_fortune = calculate_monthly_fortune(
        result_data,
        parsed_target_year,
        analysis_context=analysis_context,
    )
    weekly_fortune = build_weekly_fortune(
        result_data,
        parsed_target_date,
        gender=gender,
        daewoon=daewoon,
    )
    tomorrow_target_date = parsed_target_date + timedelta(days=1)
    tomorrow_year_fortune = (
        calculate_yearly_fortune(result_data, daewoon, tomorrow_target_date.year) if daewoon else None
    )
    tomorrow_fortune = calculate_daily_fortune_for_weekly(
        result_data,
        tomorrow_target_date,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=tomorrow_year_fortune,
    )
    career_fortune = build_career_fortune(result_data, year_fortune, analysis_context=analysis_context)
    relationship_fortune = build_relationship_fortune(
        gender,
        year_fortune,
        result_data,
        analysis_context=analysis_context,
    )
    interpretation = build_interpretation(
        element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        saju_result=result_data,
        analysis_context=analysis_context,
    )
    summary_card = build_summary_card(
        element_analysis=element_analysis,
        year_fortune=year_fortune,
        career_fortune=career_fortune,
        relationship_fortune=relationship_fortune,
        ten_gods=ten_gods,
        saju_result=result_data,
    )

    result_data["raw_input"].update(
        {
            "gender": gender,
            "target_year": parsed_target_year,
            "target_month": parsed_target_month,
            "target_date": parsed_target_date.isoformat(),
            "saju_id": result_data["saju_id"],
        }
    )
    result_data["cache_key"] = analysis_context_cache_key
    result_data["normalized_solar_input"] = result_data["resolved_solar"]
    result_data["report_generated_on"] = _today_in_seoul().isoformat()
    result_data.update(element_analysis)
    result_data.update(ten_gods)
    result_data.update(interpretation)
    result_data["daewoon"] = daewoon
    result_data["year_fortune"] = year_fortune
    result_data["monthly_fortune"] = monthly_fortune
    result_data["selected_month_fortune"] = (
        next((item for item in monthly_fortune if item["month"] == parsed_target_month), None)
        if parsed_target_month is not None
        else None
    )
    result_data["daily_fortune"] = daily_fortune
    result_data["tomorrow_fortune"] = tomorrow_fortune
    result_data["weekly_fortune"] = weekly_fortune
    result_data["career_fortune"] = career_fortune
    result_data["relationship_fortune"] = relationship_fortune
    result_data["summary_card"] = summary_card
    result_data["analysis_context"] = analysis_context
    result_data["interpretation_signals"] = interpretation_signals
    result_data["structured_report"] = structured_report
    result_data["premium_report"] = build_premium_report(
        saju_result=result_data,
        element_analysis=element_analysis,
        ten_gods=ten_gods,
        daewoon=daewoon,
        year_fortune=year_fortune,
        career_fortune=career_fortune,
        relationship_fortune=relationship_fortune,
        interpretation=interpretation,
        premium_enabled=_is_checked(premium),
        analysis_context=analysis_context,
    )
    return form_data, result_data


def _build_pdf_response(request: Request, result_data: dict) -> Response:
    """Render the PDF-only template and return it as a downloadable file."""
    if not result_data.get("premium_report", {}).get("enabled"):
        raise SajuCalculationError("PDF 다운로드는 프리미엄 리포트에서만 제공됩니다.")
    pdf_bytes = generate_pdf_bytes(result_data, base_url=str(request.base_url))
    filename = f"saju-report-{result_data['report_generated_on'].replace('-', '')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _display_result(result_data: dict) -> dict:
    """Return a user-facing display copy for templates."""
    return build_display_result(result_data)


@app.get("/")
async def index(request: Request):
    """Render the birth info input form."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=_build_index_context(),
    )


@app.post("/api/sentences/filter")
async def api_filter_sentences(payload: dict | None = None):
    """Run duplicate/quality filtering and save the refined sentence DB."""
    data = payload or {}
    try:
        threshold = float(data.get("threshold", 0.85))
        min_quality = int(data.get("min_quality", 60))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="threshold/min_quality 형식이 올바르지 않습니다.") from exc

    if not 0.0 <= threshold <= 1.0:
        raise HTTPException(status_code=400, detail="threshold는 0~1 범위여야 합니다.")
    if not 0 <= min_quality <= 100:
        raise HTTPException(status_code=400, detail="min_quality는 0~100 범위여야 합니다.")

    summary = SentenceFilter().filter_and_save(threshold=threshold, min_quality=min_quality)
    clear_sentence_db_cache()
    return summary


@app.post("/api/result")
async def api_result(saju_input: dict):
    """Return analysis+report payload from direct pillar input."""
    chart = saju_input.get("saju", saju_input)
    if not isinstance(chart, dict):
        raise HTTPException(status_code=400, detail="입력 형식이 올바르지 않습니다.")

    if "hour" in chart and "time" not in chart:
        chart = {**chart, "time": chart["hour"]}

    for key in ("year", "month", "day"):
        if key not in chart or not isinstance(chart[key], dict):
            raise HTTPException(status_code=400, detail=f"{key} 기둥 정보가 필요합니다.")
        if "stem" not in chart[key] or "branch" not in chart[key]:
            raise HTTPException(status_code=400, detail=f"{key} 기둥은 stem/branch를 포함해야 합니다.")

    analyzer = StructureAnalyzer()
    matcher = SentenceMatcher()
    builder = ReportBuilder(matcher)
    analysis = analyzer.analyze(chart)
    report = builder.build(analysis)
    return {"analysis": analysis, "report": report}


@app.post("/result")
async def result(
    request: Request,
    calendar_type: str = Form(...),
    year: int = Form(...),
    month: int = Form(...),
    day: int = Form(...),
    time_slot: str | None = Form(None),
    is_leap_month: str | None = Form(None),
    gender: str | None = Form(None),
    target_year: str | None = Form(None),
    target_month: str | None = Form(None),
    target_date: str | None = Form(None),
):
    """Handle form submission and render a real saju result."""
    form_data = {
        "calendar_type": calendar_type,
        "year": year,
        "month": month,
        "day": day,
        "time_slot": time_slot or "",
        "is_leap_month": _is_checked(is_leap_month),
        "gender": gender,
        "target_year": target_year or str(_today_in_seoul().year),
        "target_month": target_month or str(_today_in_seoul().month),
        "target_date": target_date or _today_in_seoul().isoformat(),
    }
    try:
        form_data, result_data = _build_result_data(
            calendar_type=calendar_type,
            year=year,
            month=month,
            day=day,
            time_slot=time_slot,
            is_leap_month=is_leap_month,
            gender=gender,
            target_year=target_year,
            target_month=target_month,
            target_date=target_date,
        )
    except SajuCalculationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_build_index_context(
                form_data=form_data,
                error_message=str(exc),
            ),
            status_code=400,
        )

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "form_data": form_data,
            "result": _display_result(result_data),
            "email_form_data": _default_email_form_data(),
            "email_error_message": None,
            "email_success_message": None,
            "premium_upgrade_link": _build_premium_upgrade_link(request, result_data),
            "premium_pdf_link": _build_premium_pdf_link(request, result_data) if result_data["premium_report"]["enabled"] else None,
        },
    )
@app.get("/report/view")
async def report_view(
    request: Request,
    calendar_type: str,
    year: int,
    month: int,
    day: int,
    time_slot: str | None = None,
    is_leap_month: str | None = None,
    gender: str | None = None,
    target_year: str | None = None,
    target_month: str | None = None,
    target_date: str | None = None,
    premium: str | None = None,
):
    """Render the detailed report by query parameters for email deep-links."""
    try:
        form_data, result_data = _build_result_data(
            calendar_type=calendar_type,
            year=year,
            month=month,
            day=day,
            time_slot=time_slot,
            is_leap_month=is_leap_month,
            gender=gender,
            target_year=target_year,
            target_month=target_month,
            target_date=target_date,
            premium=premium,
        )
    except SajuCalculationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_build_index_context(error_message=str(exc)),
            status_code=400,
        )

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "form_data": form_data,
            "result": _display_result(result_data),
            "email_form_data": _default_email_form_data(),
            "email_error_message": None,
            "email_success_message": None,
            "premium_upgrade_link": _build_premium_upgrade_link(request, result_data),
            "premium_pdf_link": _build_premium_pdf_link(request, result_data) if result_data["premium_report"]["enabled"] else None,
        },
    )
@app.get("/report/pdf")
async def report_pdf(
    request: Request,
    calendar_type: str,
    year: int,
    month: int,
    day: int,
    time_slot: str | None = None,
    is_leap_month: str | None = None,
    gender: str | None = None,
    target_year: str | None = None,
    target_month: str | None = None,
    target_date: str | None = None,
    premium: str | None = None,
):
    """Render a PDF-friendly report template from the same result data."""
    try:
        _, result_data = _build_result_data(
            calendar_type=calendar_type,
            year=year,
            month=month,
            day=day,
            time_slot=time_slot,
            is_leap_month=is_leap_month,
            gender=gender,
            target_year=target_year,
            target_month=target_month,
            target_date=target_date,
            premium=premium,
        )
    except SajuCalculationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=_build_index_context(error_message=str(exc)),
            status_code=400,
        )
    try:
        return _build_pdf_response(request, result_data)
    except SajuCalculationError as exc:
        if "프리미엄 리포트" in str(exc):
            return PlainTextResponse(str(exc), status_code=403)
        return PlainTextResponse(
            f"PDF 생성 실패: {exc}\n\n"
            "조치:\n"
            "1. pip install -r requirements.txt\n"
            "2. 서버 재시작\n",
            status_code=500,
        )
    except Exception as exc:  # pragma: no cover - defensive path for runtime PDF engine issues
        return PlainTextResponse(
            f"PDF 생성 중 예상치 못한 오류가 발생했습니다: {exc}",
            status_code=500,
        )


@app.post("/report/email")
async def report_email(
    request: Request,
    calendar_type: str = Form(...),
    year: int = Form(...),
    month: int = Form(...),
    day: int = Form(...),
    time_slot: str | None = Form(None),
    is_leap_month: str | None = Form(None),
    gender: str | None = Form(None),
    target_year: str | None = Form(None),
    target_month: str | None = Form(None),
    target_date: str | None = Form(None),
    email: str = Form(...),
    name: str | None = Form(None),
    consent: str | None = Form(None),
):
    """Send the HTML report email and persist the lead."""
    form_data = {
        "calendar_type": calendar_type,
        "year": year,
        "month": month,
        "day": day,
        "time_slot": time_slot or "",
        "is_leap_month": _is_checked(is_leap_month),
        "gender": gender,
        "target_year": target_year or str(_today_in_seoul().year),
        "target_month": target_month or str(_today_in_seoul().month),
        "target_date": target_date or _today_in_seoul().isoformat(),
    }
    email_form_data = {
        "email": email,
        "name": name or "",
        "consent": _is_checked(consent),
    }

    try:
        normalized_email = _validate_email(email)
        _check_email_rate_limit(normalized_email, _build_birth_signature(form_data))
        form_data, result_data = _build_result_data(
            calendar_type=calendar_type,
            year=year,
            month=month,
            day=day,
            time_slot=time_slot,
            is_leap_month=is_leap_month,
            gender=gender,
            target_year=target_year,
            target_month=target_month,
            target_date=target_date,
            premium=False,
        )
        detail_link = _build_report_view_link(request, result_data)
        send_report_email(
            to_email=normalized_email,
            name=name,
            result_data=_display_result(result_data),
            detail_link=detail_link,
        )
        save_lead(
            build_lead_payload(
                email=normalized_email,
                name=name,
                consent=_is_checked(consent),
                result_data=result_data,
            )
        )
        _mark_email_rate_limit(normalized_email, _build_birth_signature(form_data))
        logger.info("Email report sent and lead saved for %s", normalized_email)
        email_success_message = "리포트가 이메일로 전송되었습니다."
        email_error_message = None
        email_form_data["email"] = normalized_email
    except SajuCalculationError as exc:
        logger.warning("Failed to process email report request for %s: %s", email, exc)
        try:
            form_data, result_data = _build_result_data(
                calendar_type=calendar_type,
                year=year,
                month=month,
                day=day,
                time_slot=time_slot,
                is_leap_month=is_leap_month,
                gender=gender,
                target_year=target_year,
                target_month=target_month,
                target_date=target_date,
            )
        except SajuCalculationError:
            return templates.TemplateResponse(
                request=request,
                name="index.html",
                context=_build_index_context(
                    form_data=form_data,
                    error_message=str(exc),
                    email_form_data=email_form_data,
                ),
                status_code=400,
            )
        email_success_message = None
        email_error_message = str(exc)
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "form_data": form_data,
                "result": _display_result(result_data),
                "email_form_data": email_form_data,
                "email_error_message": email_error_message,
                "email_success_message": email_success_message,
                "premium_upgrade_link": _build_premium_upgrade_link(request, result_data),
                "premium_pdf_link": _build_premium_pdf_link(request, result_data) if result_data["premium_report"]["enabled"] else None,
            },
            status_code=400,
        )

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "form_data": form_data,
            "result": _display_result(result_data),
            "email_form_data": email_form_data,
            "email_error_message": email_error_message,
            "email_success_message": email_success_message,
            "premium_upgrade_link": _build_premium_upgrade_link(request, result_data),
            "premium_pdf_link": _build_premium_pdf_link(request, result_data) if result_data["premium_report"]["enabled"] else None,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
