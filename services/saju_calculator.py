"""Real saju calculator based on Korean lunar conversion and solar terms."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import logging

from korean_lunar_calendar import KoreanLunarCalendar
from lunar_python import Solar

from data.branches import BRANCHES
from data.stems import STEMS
from services.identification import build_saju_identity

try:
    import sxtwl  # type: ignore
except ImportError:  # pragma: no cover - optional diagnostic dependency
    sxtwl = None


logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE_OFFSET_HOURS = 9
LUNAR_PYTHON_BASE_TIMEZONE_OFFSET_HOURS = 8
DAY_PILLAR_EPOCH_DATE = date(2000, 1, 7)
DAY_PILLAR_EPOCH_JDN = 2451551
DAY_PILLAR_EPOCH_GANZHI = "갑자"
TIME_SLOT_OPTIONS = (
    {"id": "", "label": "시간 미상", "hour": None, "minute": None, "branch_index": None, "branch": None},
    {"id": "early_ja", "label": "자시 (00:00~00:59)", "hour": 0, "minute": 30, "branch_index": 0, "branch": "자"},
    {"id": "chuk", "label": "축시 (01:00~02:59)", "hour": 1, "minute": 30, "branch_index": 1, "branch": "축"},
    {"id": "in", "label": "인시 (03:00~04:59)", "hour": 3, "minute": 30, "branch_index": 2, "branch": "인"},
    {"id": "myo", "label": "묘시 (05:00~06:59)", "hour": 5, "minute": 30, "branch_index": 3, "branch": "묘"},
    {"id": "jin", "label": "진시 (07:00~08:59)", "hour": 7, "minute": 30, "branch_index": 4, "branch": "진"},
    {"id": "sa", "label": "사시 (09:00~10:59)", "hour": 9, "minute": 30, "branch_index": 5, "branch": "사"},
    {"id": "o", "label": "오시 (11:00~12:59)", "hour": 11, "minute": 30, "branch_index": 6, "branch": "오"},
    {"id": "mi", "label": "미시 (13:00~14:59)", "hour": 13, "minute": 30, "branch_index": 7, "branch": "미"},
    {"id": "sin", "label": "신시 (15:00~16:59)", "hour": 15, "minute": 30, "branch_index": 8, "branch": "신"},
    {"id": "yu", "label": "유시 (17:00~18:59)", "hour": 17, "minute": 30, "branch_index": 9, "branch": "유"},
    {"id": "sul", "label": "술시 (19:00~20:59)", "hour": 19, "minute": 30, "branch_index": 10, "branch": "술"},
    {"id": "hae", "label": "해시 (21:00~22:59)", "hour": 21, "minute": 30, "branch_index": 11, "branch": "해"},
    {"id": "late_ja", "label": "자시 (23:00~23:59)", "hour": 23, "minute": 30, "branch_index": 0, "branch": "자"},
)
SOLAR_TERM_NAMES = {
    "小寒": "소한",
    "立春": "입춘",
    "惊蛰": "경칩",
    "清明": "청명",
    "立夏": "입하",
    "芒种": "망종",
    "小暑": "소서",
    "立秋": "입추",
    "白露": "백로",
    "寒露": "한로",
    "立冬": "입동",
    "大雪": "대설",
}
MAJOR_SOLAR_TERMS = tuple(SOLAR_TERM_NAMES.keys())
HANJA_TO_KOR_STEM = {item["hanja"]: item["kor"] for item in STEMS}
HANJA_TO_KOR_BRANCH = {item["hanja"]: item["kor"] for item in BRANCHES}
TIME_SLOT_BY_ID = {item["id"]: item for item in TIME_SLOT_OPTIONS}


class SajuCalculationError(ValueError):
    """Raised when accurate saju calculation cannot be completed."""


@dataclass(frozen=True)
class SolarTermPoint:
    """Major solar-term instant converted to Korea time."""

    name: str
    at: datetime


@dataclass(frozen=True)
class DayPillarDiagnostics:
    """Comparison data for validating the day pillar calculation."""

    local_iso: str
    utc_iso: str | None
    local_date: str
    utc_date: str | None
    jdn: int
    epoch_date: str
    epoch_ganzhi: str
    epoch_offset_days: int
    independent_day: str
    lunar_python_day: str
    korean_lunar_calendar_day: str
    sxtwl_day: str | None
    all_methods_match: bool


def get_basic_saju_result(
    calendar_type: str,
    year: int,
    month: int,
    day: int,
    hour: int | None = None,
    minute: int | None = None,
    time_slot: str | None = None,
    is_leap_month: bool = False,
) -> dict:
    """Return a real saju result using Korean lunar conversion and solar terms."""
    _validate_inputs(
        calendar_type=calendar_type,
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        time_slot=time_slot,
        is_leap_month=is_leap_month,
    )

    resolved_time = _resolve_birth_time(hour=hour, minute=minute, time_slot=time_slot)
    hour = resolved_time["hour"] if resolved_time else None
    minute = resolved_time["minute"] if resolved_time else None

    solar_date = _resolve_solar_date(
        calendar_type=calendar_type,
        year=year,
        month=month,
        day=day,
        is_leap_month=is_leap_month,
    )
    birth_moment = _build_birth_moment(
        solar_date=solar_date,
        hour=hour,
        minute=minute,
        timezone_offset_hours=DEFAULT_TIMEZONE_OFFSET_HOURS,
    )

    if hour is None:
        _raise_if_boundary_day_without_time(solar_date)

    shifted_birth_moment = _shift_for_lunar_python_boundary(birth_moment)
    shifted_reference_moment = _shift_for_lunar_python_boundary(_as_noon(solar_date))

    year_month_source = shifted_birth_moment or shifted_reference_moment
    local_source = birth_moment or _as_noon(solar_date)
    year_month_eight_char = _get_eight_char(year_month_source)
    local_eight_char = _get_eight_char(local_source)
    day_pillar = _calculate_day_pillar(solar_date)
    time_pillar = (
        _calculate_time_pillar(day_pillar["stem"], resolved_time["branch_index"]) if resolved_time else None
    )
    day_diagnostics = _build_day_pillar_diagnostics(
        solar_date=solar_date,
        local_source=local_source,
        lunar_python_day=local_eight_char.getDay(),
        independent_day=day_pillar["hanja"],
    )
    sensitivity = _build_sensitivity_hooks(
        solar_date=solar_date,
        local_source=local_source,
        birth_moment=birth_moment,
    )
    _log_day_pillar_diagnostics(day_diagnostics)

    saju = {
        "year": _build_pillar_from_hanja(year_month_eight_char.getYear()),
        "month": _build_pillar_from_hanja(year_month_eight_char.getMonth()),
        "day": day_pillar,
        "time": time_pillar,
    }
    identity = build_saju_identity(saju)

    return {
        "saju": saju,
        **identity,
        "raw_input": {
            "calendar_type": calendar_type,
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minute": minute,
            "time_slot": time_slot,
            "is_leap_month": is_leap_month,
        },
        "time_basis": resolved_time,
        "resolved_solar": {
            "year": solar_date.year,
            "month": solar_date.month,
            "day": solar_date.day,
            "iso": solar_date.isoformat(),
        },
        "calculation_basis": {
            "timezone": "Asia/Seoul",
            "year_boundary": "입춘 기준",
            "month_boundary": "절입(12절기) 기준",
            "day_boundary": "한국 기준 양력 civil date를 JDN으로 변환 후 2000-01-07 갑자일 epoch 기준 60갑자 계산",
            "time_boundary": "입력 시간 구간을 사주 기준 시각으로 변환한 뒤 일간 기준 시주 공식 사용",
        },
        "sensitivity": sensitivity,
        "debug": {
            "day_pillar": day_diagnostics.__dict__,
        },
    }


def build_korean_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 12,
    minute: int = 0,
) -> datetime:
    """Build a timezone-aware datetime in Asia/Seoul."""
    tzinfo = timezone(timedelta(hours=DEFAULT_TIMEZONE_OFFSET_HOURS))
    return datetime(year, month, day, hour, minute, tzinfo=tzinfo)


def get_year_month_pillars_for_datetime(moment: datetime) -> dict:
    """Return year and month pillars for a Korea-time birth moment."""
    shifted_moment = _shift_for_lunar_python_boundary(moment)
    eight_char = _get_eight_char(shifted_moment)
    return {
        "year": _build_pillar_from_hanja(eight_char.getYear()),
        "month": _build_pillar_from_hanja(eight_char.getMonth()),
    }


def get_day_pillar_for_solar_date(solar_date: date) -> dict:
    """Return the day pillar for a solar civil date in Korea."""
    return _calculate_day_pillar(solar_date)


def get_time_pillar_for_day_stem(day_stem_kor: str, hour: int | None) -> dict | None:
    """Return the time pillar for a given day stem and hour."""
    if hour is None:
        return None
    return _calculate_time_pillar(day_stem_kor, _resolve_saju_branch_index(hour))


def get_major_solar_term_points(year: int) -> tuple[SolarTermPoint, ...]:
    """Expose major solar-term points for fortune calculations."""
    return _get_major_term_points(year)


def _validate_inputs(
    calendar_type: str,
    year: int,
    month: int,
    day: int,
    hour: int | None,
    minute: int | None,
    time_slot: str | None,
    is_leap_month: bool,
) -> None:
    if calendar_type not in {"solar", "lunar"}:
        raise SajuCalculationError("달력 종류는 solar 또는 lunar 여야 합니다.")

    if hour is None and minute is not None:
        raise SajuCalculationError("출생분을 입력하려면 출생시간도 함께 입력해야 합니다.")

    if hour is not None and not 0 <= hour <= 23:
        raise SajuCalculationError("출생시간은 0부터 23 사이여야 합니다.")

    if minute is not None and not 0 <= minute <= 59:
        raise SajuCalculationError("출생분은 0부터 59 사이여야 합니다.")

    if time_slot is not None and time_slot not in TIME_SLOT_BY_ID:
        raise SajuCalculationError("출생시간 구간 선택이 올바르지 않습니다.")

    if time_slot and (hour is not None or minute is not None):
        raise SajuCalculationError("출생시간은 구간 선택 또는 직접 시각 입력 중 하나만 사용해 주세요.")

    if calendar_type == "solar" and is_leap_month:
        raise SajuCalculationError("윤달 선택은 음력 입력에서만 사용할 수 있습니다.")

    if calendar_type == "solar":
        try:
            date(year, month, day)
        except ValueError as exc:
            raise SajuCalculationError("유효한 양력 날짜를 입력해 주세요.") from exc


def _resolve_solar_date(
    calendar_type: str,
    year: int,
    month: int,
    day: int,
    is_leap_month: bool,
) -> date:
    if calendar_type == "solar":
        return date(year, month, day)

    calendar = KoreanLunarCalendar()
    is_valid = calendar.setLunarDate(year, month, day, is_leap_month)
    if not is_valid:
        raise SajuCalculationError("유효한 음력 날짜가 아니거나 지원 범위를 벗어났습니다.")

    solar_year, solar_month, solar_day = map(int, calendar.SolarIsoFormat().split("-"))
    return date(solar_year, solar_month, solar_day)


def _build_birth_moment(
    solar_date: date,
    hour: int | None,
    minute: int | None,
    timezone_offset_hours: int,
) -> datetime | None:
    if hour is None:
        return None

    tzinfo = timezone(timedelta(hours=timezone_offset_hours))
    return datetime(
        solar_date.year,
        solar_date.month,
        solar_date.day,
        hour,
        minute or 0,
        tzinfo=tzinfo,
    )


def _raise_if_boundary_day_without_time(solar_date: date) -> None:
    for point in _get_major_term_points(solar_date.year - 1) + _get_major_term_points(solar_date.year):
        if point.at.date() == solar_date:
            raise SajuCalculationError(
                f"{solar_date.isoformat()}은 {SOLAR_TERM_NAMES[point.name]} 절입일입니다. "
                "정확한 년주/월주 판정을 위해 출생시간을 입력해 주세요."
            )


def _build_sensitivity_hooks(
    *,
    solar_date: date,
    local_source: datetime,
    birth_moment: datetime | None,
) -> dict:
    major_terms = sorted(
        _get_major_term_points(solar_date.year - 1)
        + _get_major_term_points(solar_date.year)
        + _get_major_term_points(solar_date.year + 1),
        key=lambda point: point.at,
    )
    previous_term = None
    next_term = None
    for point in major_terms:
        if point.at <= local_source:
            previous_term = point
            continue
        next_term = point
        break

    nearest_gap_hours = None
    if previous_term and next_term:
        previous_gap = abs((local_source - previous_term.at).total_seconds()) / 3600
        next_gap = abs((next_term.at - local_source).total_seconds()) / 3600
        nearest_gap_hours = round(min(previous_gap, next_gap), 2)
    elif previous_term:
        nearest_gap_hours = round(abs((local_source - previous_term.at).total_seconds()) / 3600, 2)
    elif next_term:
        nearest_gap_hours = round(abs((next_term.at - local_source).total_seconds()) / 3600, 2)

    notes: list[str] = []
    if birth_moment is None:
        notes.append("출생시간이 없어 시주와 경계 시각 민감도는 보수적으로 읽습니다.")
    if birth_moment and birth_moment.hour in {23, 0}:
        notes.append("자시 전후 출생이라 일주/시주 경계 해석을 함께 보는 편이 안전합니다.")
    if nearest_gap_hours is not None and nearest_gap_hours <= 24:
        notes.append("절입과 가까운 시점이라 월주/연주 판정 민감도를 함께 볼 필요가 있습니다.")

    return {
        "late_night_birth": bool(birth_moment and birth_moment.hour in {23, 0}),
        "near_major_solar_term": bool(nearest_gap_hours is not None and nearest_gap_hours <= 24),
        "nearest_major_term_gap_hours": nearest_gap_hours,
        "previous_major_term": None if previous_term is None else {
            "name": SOLAR_TERM_NAMES[previous_term.name],
            "at": previous_term.at.isoformat(),
        },
        "next_major_term": None if next_term is None else {
            "name": SOLAR_TERM_NAMES[next_term.name],
            "at": next_term.at.isoformat(),
        },
        "notes": notes,
    }


def _build_pillar_from_hanja(value: str) -> dict:
    if len(value) != 2:
        raise SajuCalculationError(f"간지 형식이 올바르지 않습니다: {value}")

    stem = value[0]
    branch = value[1]
    return {
        "kor": f"{HANJA_TO_KOR_STEM[stem]}{HANJA_TO_KOR_BRANCH[branch]}",
        "hanja": value,
        "stem": HANJA_TO_KOR_STEM[stem],
        "branch": HANJA_TO_KOR_BRANCH[branch],
        "stem_hanja": stem,
        "branch_hanja": branch,
    }


def _build_pillar_from_indices(stem_index: int, branch_index: int) -> dict:
    stem = STEMS[stem_index]
    branch = BRANCHES[branch_index]
    return {
        "kor": f"{stem['kor']}{branch['kor']}",
        "hanja": f"{stem['hanja']}{branch['hanja']}",
        "stem": stem["kor"],
        "branch": branch["kor"],
        "stem_hanja": stem["hanja"],
        "branch_hanja": branch["hanja"],
    }


def _as_noon(solar_date: date) -> datetime:
    return datetime(
        solar_date.year,
        solar_date.month,
        solar_date.day,
        12,
        0,
        tzinfo=timezone(timedelta(hours=DEFAULT_TIMEZONE_OFFSET_HOURS)),
    )


@lru_cache(maxsize=None)
def _get_major_term_points(year: int) -> tuple[SolarTermPoint, ...]:
    sample_lunar = Solar.fromYmdHms(year, 6, 1, 12, 0, 0).getLunar()
    jie_qi_table = sample_lunar.getJieQiTable()
    points = []
    for name in MAJOR_SOLAR_TERMS:
        solar = jie_qi_table.get(name)
        if solar is None:
            continue
        points.append(SolarTermPoint(name=name, at=_solar_to_korean_datetime(solar)))
    unique_points = sorted({(point.name, point.at) for point in points}, key=lambda item: item[1])
    return tuple(SolarTermPoint(name=name, at=at) for name, at in unique_points)


def _get_eight_char(moment: datetime):
    solar = Solar.fromYmdHms(
        moment.year,
        moment.month,
        moment.day,
        moment.hour,
        moment.minute,
        moment.second,
    )
    return solar.getLunar().getEightChar()


def _calculate_day_pillar(solar_date: date) -> dict:
    """
    Calculate the day pillar from a fixed civil-date epoch.

    The epoch is 2000-01-07 = 갑자일, which matches korean_lunar_calendar and sxtwl
    for the reference dates used in this project.
    """
    jdn = _gregorian_date_to_jdn(solar_date.year, solar_date.month, solar_date.day)
    cycle_index = (jdn - DAY_PILLAR_EPOCH_JDN) % 60
    return _build_pillar_from_indices(cycle_index % 10, cycle_index % 12)


def _calculate_time_pillar(day_stem_kor: str, time_branch_index: int | None) -> dict | None:
    if time_branch_index is None:
        return None

    day_stem_index = next(
        index for index, stem in enumerate(STEMS) if stem["kor"] == day_stem_kor
    )
    time_start_stem_index = {
        0: 0,
        5: 0,
        1: 2,
        6: 2,
        2: 4,
        7: 4,
        3: 6,
        8: 6,
        4: 8,
        9: 8,
    }[day_stem_index]
    time_stem_index = (time_start_stem_index + time_branch_index) % 10
    return _build_pillar_from_indices(time_stem_index, time_branch_index)


def get_time_slot_options() -> tuple[dict, ...]:
    """Expose time-slot options for the HTML form."""
    return TIME_SLOT_OPTIONS


def _resolve_birth_time(
    hour: int | None,
    minute: int | None,
    time_slot: str | None,
) -> dict | None:
    if time_slot:
        slot = dict(TIME_SLOT_BY_ID[time_slot])
        if slot["branch"] is None:
            return None
        return {
            "input_label": slot["label"],
            "hour": slot["hour"],
            "minute": slot["minute"],
            "branch_index": slot["branch_index"],
            "saju_time_kor": f"{slot['branch']}시",
            "saju_branch": slot["branch"],
            "time_range": "23:00~00:59" if slot["branch"] == "자" else slot["label"].split("(", 1)[1][:-1],
        }

    if hour is None:
        return None

    time_branch_index = _resolve_saju_branch_index(hour)
    branch = BRANCHES[time_branch_index]["kor"]
    display_minute = minute if minute is not None else 0
    return {
        "input_label": f"{hour:02d}시 {display_minute:02d}분",
        "hour": hour,
        "minute": display_minute,
        "branch_index": time_branch_index,
        "saju_time_kor": f"{branch}시",
        "saju_branch": branch,
        "time_range": "23:00~00:59" if branch == "자" else _build_time_range_label(time_branch_index),
    }


def _resolve_saju_branch_index(hour: int) -> int:
    if hour in {23, 0}:
        return 0
    return ((hour - 1) // 2) + 1


def _build_time_range_label(branch_index: int) -> str:
    start_hour = (branch_index * 2) - 1
    end_hour = start_hour + 1
    return f"{start_hour:02d}:00~{end_hour:02d}:59"


def _gregorian_date_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + ((153 * m + 2) // 5) + 365 * y + (y // 4) - (y // 100) + (y // 400) - 32045


def _build_day_pillar_diagnostics(
    solar_date: date,
    local_source: datetime,
    lunar_python_day: str,
    independent_day: str,
) -> DayPillarDiagnostics:
    utc_source = local_source.astimezone(timezone.utc) if local_source.tzinfo else None
    kari_day = _get_korean_lunar_calendar_day_pillar(solar_date)
    sxtwl_day = _get_sxtwl_day_pillar(solar_date)

    compared = [independent_day, lunar_python_day, kari_day]
    if sxtwl_day is not None:
        compared.append(sxtwl_day)

    return DayPillarDiagnostics(
        local_iso=local_source.isoformat(),
        utc_iso=utc_source.isoformat() if utc_source else None,
        local_date=solar_date.isoformat(),
        utc_date=utc_source.date().isoformat() if utc_source else None,
        jdn=_gregorian_date_to_jdn(solar_date.year, solar_date.month, solar_date.day),
        epoch_date=DAY_PILLAR_EPOCH_DATE.isoformat(),
        epoch_ganzhi=DAY_PILLAR_EPOCH_GANZHI,
        epoch_offset_days=_gregorian_date_to_jdn(solar_date.year, solar_date.month, solar_date.day)
        - DAY_PILLAR_EPOCH_JDN,
        independent_day=independent_day,
        lunar_python_day=lunar_python_day,
        korean_lunar_calendar_day=kari_day,
        sxtwl_day=sxtwl_day,
        all_methods_match=len(set(compared)) == 1,
    )


def _get_korean_lunar_calendar_day_pillar(solar_date: date) -> str:
    calendar = KoreanLunarCalendar()
    calendar.setSolarDate(solar_date.year, solar_date.month, solar_date.day)
    day_token = calendar.getGapJaString().split()[2].replace("일", "")
    return _kor_to_hanja(day_token)


def _get_sxtwl_day_pillar(solar_date: date) -> str | None:
    if sxtwl is None:
        return None

    gz = sxtwl.fromSolar(solar_date.year, solar_date.month, solar_date.day).getDayGZ()
    return f"{STEMS[gz.tg]['hanja']}{BRANCHES[gz.dz]['hanja']}"


def _kor_to_hanja(value: str) -> str:
    if len(value) != 2:
        raise SajuCalculationError(f"한글 간지 형식이 올바르지 않습니다: {value}")

    stem_hanja = next(item["hanja"] for item in STEMS if item["kor"] == value[0])
    branch_hanja = next(item["hanja"] for item in BRANCHES if item["kor"] == value[1])
    return f"{stem_hanja}{branch_hanja}"


def _log_day_pillar_diagnostics(diagnostics: DayPillarDiagnostics) -> None:
    logger.info(
        "Day pillar diagnostics | local=%s utc=%s local_date=%s utc_date=%s jdn=%s epoch=%s(%s) "
        "offset_days=%s independent=%s lunar_python=%s korean_lunar_calendar=%s sxtwl=%s match=%s",
        diagnostics.local_iso,
        diagnostics.utc_iso,
        diagnostics.local_date,
        diagnostics.utc_date,
        diagnostics.jdn,
        diagnostics.epoch_date,
        diagnostics.epoch_ganzhi,
        diagnostics.epoch_offset_days,
        diagnostics.independent_day,
        diagnostics.lunar_python_day,
        diagnostics.korean_lunar_calendar_day,
        diagnostics.sxtwl_day,
        diagnostics.all_methods_match,
    )


def _shift_for_lunar_python_boundary(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None

    # lunar_python computes exact solar-term boundaries in UTC+8.
    # Shift KST input by -1 hour so year/month boundaries match Korea time.
    return moment - timedelta(
        hours=DEFAULT_TIMEZONE_OFFSET_HOURS - LUNAR_PYTHON_BASE_TIMEZONE_OFFSET_HOURS
    )


def _solar_to_korean_datetime(solar) -> datetime:
    source = datetime.strptime(solar.toYmdHms(), "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=timezone(timedelta(hours=LUNAR_PYTHON_BASE_TIMEZONE_OFFSET_HOURS))
    )
    return source.astimezone(timezone(timedelta(hours=DEFAULT_TIMEZONE_OFFSET_HOURS)))
