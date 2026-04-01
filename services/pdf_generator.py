"""PDF generation service kept for internal reuse."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from services.saju_calculator import SajuCalculationError

TEMPLATE_DIR = Path("templates")


def generate_pdf_bytes(result_data: dict, base_url: str) -> bytes:
    """Render the PDF report template and return PDF bytes."""
    try:
        from weasyprint import HTML
    except ImportError as exc:  # pragma: no cover - depends on runtime environment
        raise SajuCalculationError("PDF 생성을 위해 weasyprint 설치가 필요합니다.") from exc

    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = environment.get_template("report_pdf.html").render(result=result_data)
    try:
        return HTML(string=html, base_url=base_url).write_pdf()
    except Exception as exc:  # pragma: no cover - runtime dependency issue path
        raise SajuCalculationError(f"PDF 생성 엔진 실행에 실패했습니다: {exc}") from exc
