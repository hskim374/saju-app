"""SMTP-based HTML report email sender."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from services.saju_calculator import SajuCalculationError

logger = logging.getLogger(__name__)
TEMPLATE_DIR = Path("templates")


def send_report_email(
    *,
    to_email: str,
    name: str | None,
    result_data: dict,
    detail_link: str,
) -> None:
    """Send an HTML report email through SMTP."""
    message = EmailMessage()
    message["Subject"] = _env("SMTP_SUBJECT_PREFIX", "[saju-mvp]") + " 사주 리포트"
    message["From"] = _build_from_header()
    message["To"] = to_email
    message.set_content("HTML 메일을 확인해 주세요.")
    message.add_alternative(
        _render_email_html(name=name, result_data=result_data, detail_link=detail_link),
        subtype="html",
    )

    host = _required_env("SMTP_HOST")
    port = int(_env("SMTP_PORT", "587"))
    username = _required_env("SMTP_USERNAME")
    password = _required_env("SMTP_PASSWORD")
    use_tls = _env("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            if use_tls:
                server.starttls()
            server.login(username, password)
            server.send_message(message)
    except Exception as exc:
        logger.exception("Failed to send report email to %s", to_email)
        raise SajuCalculationError("이메일 발송에 실패했습니다. 잠시 후 다시 시도해 주세요.") from exc

    logger.info("Report email sent to %s", to_email)


def _render_email_html(*, name: str | None, result_data: dict, detail_link: str) -> str:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return environment.get_template("email_report.html").render(
        result=result_data,
        recipient_name=name or "고객",
        detail_link=detail_link,
    )


def _build_from_header() -> str:
    from_email = _required_env("SMTP_FROM_EMAIL")
    from_name = _env("SMTP_FROM_NAME", "saju-mvp")
    return f"{from_name} <{from_email}>"


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SajuCalculationError(f"{name} 환경변수가 필요합니다.")
    return value


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)
