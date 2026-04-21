"""OpenAI-based premium report generator."""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import urllib.error
import urllib.request
from datetime import datetime
import time
from typing import Any

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"
DEFAULT_TIMEOUT_SECONDS = 100
DEFAULT_RETRY_COUNT = 1
DEFAULT_MAX_OUTPUT_TOKENS = 3000
DEFAULT_MAX_OUTPUT_RETRY_STEPS = 2
DEFAULT_MAX_OUTPUT_TOKENS_CAP = 12000
DEFAULT_PROMPT_TEMPLATE_PATH = "data/prompts/premium_report_prompt.txt"
DEFAULT_DEBUG_DUMP_DIR = "logs/ai_premium"
DEBUG_LOG_RETENTION_DAYS = 2

SYSTEM_PROMPT = (
    "너는 한국어 사주 리포트 편집기다. "
    "입력 데이터를 바탕으로 premium_report JSON만 생성한다. "
    "마크다운, 코드블록, 설명문 없이 JSON 객체만 반환한다."
)

DEFAULT_USER_PROMPT_TEMPLATE = (
    "다음 입력 데이터를 바탕으로 프리미엄 사주 리포트를 생성해라.\n"
    "- 출력 언어: 한국어\n"
    "- 문체: 생활형, 직관적, 단정적 과장은 피함\n"
    "- 출력 형식: 아래 스키마와 동일한 JSON\n"
    "- 최소 섹션 수: 4 (personality, money, relationship, career)\n\n"
    "출력 스키마 예시:\n{{SCHEMA_JSON}}\n\n"
    "입력 데이터:\n{{INPUT_JSON}}"
)


def _resolve_model(model: str | None) -> str:
    env_model = os.getenv("OPENAI_MODEL", "").strip()
    return model.strip() if isinstance(model, str) and model.strip() else (env_model or DEFAULT_OPENAI_MODEL)


def _resolve_timeout_seconds(timeout_seconds: int | None) -> int:
    if isinstance(timeout_seconds, int) and timeout_seconds > 0:
        return timeout_seconds
    raw = os.getenv("OPENAI_TIMEOUT_SECONDS", "").strip()
    if raw.isdigit():
        value = int(raw)
        if value > 0:
            return value
    return DEFAULT_TIMEOUT_SECONDS


def _resolve_retry_count() -> int:
    raw = os.getenv("OPENAI_RETRY_COUNT", "").strip()
    if raw.isdigit():
        return max(0, int(raw))
    return DEFAULT_RETRY_COUNT


def _resolve_max_output_tokens() -> int:
    raw = os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "").strip()
    if raw.isdigit():
        value = int(raw)
        if value > 0:
            return value
    return DEFAULT_MAX_OUTPUT_TOKENS


def _resolve_max_output_retry_steps() -> int:
    raw = os.getenv("OPENAI_MAX_OUTPUT_RETRY_STEPS", "").strip()
    if raw.isdigit():
        return max(0, int(raw))
    return DEFAULT_MAX_OUTPUT_RETRY_STEPS


def _resolve_max_output_tokens_cap(base_tokens: int) -> int:
    raw = os.getenv("OPENAI_MAX_OUTPUT_TOKENS_CAP", "").strip()
    if raw.isdigit():
        value = int(raw)
        if value > 0:
            return max(value, base_tokens)
    return max(DEFAULT_MAX_OUTPUT_TOKENS_CAP, base_tokens)


def _is_timeout_like_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return True
        if isinstance(reason, str) and "timed out" in reason.lower():
            return True
    text = str(exc).lower()
    return "timed out" in text or "time out" in text


def _is_max_output_incomplete(response_data: dict[str, Any]) -> bool:
    status = str(response_data.get("status") or "").lower()
    if status != "incomplete":
        return False
    incomplete = response_data.get("incomplete_details")
    if isinstance(incomplete, dict):
        reason = str(incomplete.get("reason") or "").lower()
        return reason == "max_output_tokens"
    return False


def _request_openai_responses_api(
    *,
    api_key: str,
    request_body: dict[str, Any],
    timeout_seconds: int,
    retry_count: int,
) -> dict[str, Any]:
    req = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    body = ""
    last_timeout_error: BaseException | None = None
    for attempt in range(retry_count + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
            last_timeout_error = None
            break
        except urllib.error.HTTPError as exc:  # pragma: no cover - runtime network path
            error_body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI API 요청 실패 ({exc.code}): {error_body}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - runtime network path
            if _is_timeout_like_error(exc):
                last_timeout_error = exc
                if attempt < retry_count:
                    continue
                break
            raise RuntimeError(f"OpenAI API 연결 실패: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:  # pragma: no cover - runtime network path
            last_timeout_error = exc
            if attempt < retry_count:
                continue
            break

    if last_timeout_error is not None:
        raise RuntimeError(
            f"OpenAI API 응답 시간 초과 ({timeout_seconds}초). "
            "OPENAI_TIMEOUT_SECONDS를 늘리거나 OPENAI_RETRY_COUNT를 조정해 주세요."
        ) from last_timeout_error

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI API 응답이 JSON 형식이 아닙니다.") from exc


def _resolve_prompt_template(provided_template: str | None) -> str:
    if isinstance(provided_template, str) and provided_template.strip():
        return provided_template.strip()

    env_path = os.getenv("OPENAI_PREMIUM_PROMPT_FILE", "").strip() or DEFAULT_PROMPT_TEMPLATE_PATH
    path = Path(env_path)
    if path.exists() and path.is_file():
        try:
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return text
        except OSError:
            pass
    return DEFAULT_USER_PROMPT_TEMPLATE


def _resolve_debug_dump_dir() -> Path | None:
    enabled = os.getenv("OPENAI_PREMIUM_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
    raw_dir = os.getenv("OPENAI_PREMIUM_DEBUG_DIR", "").strip()
    if not enabled and not raw_dir:
        return None

    path = Path(raw_dir or DEFAULT_DEBUG_DUMP_DIR)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return path


def _dump_debug_json(debug_dir: Path | None, name: str, payload: Any) -> None:
    if debug_dir is None:
        return
    cutoff_ts = time.time() - (DEBUG_LOG_RETENTION_DAYS * 24 * 60 * 60)
    try:
        for path in debug_dir.iterdir():
            if not path.is_file():
                continue
            try:
                if path.stat().st_mtime < cutoff_ts:
                    path.unlink(missing_ok=True)
            except OSError:
                continue
    except OSError:
        pass

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    file_path = debug_dir / f"{timestamp}_{name}.json"
    try:
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        return


def _build_user_prompt(context: dict[str, Any], prompt_template: str | None = None) -> str:
    schema = {
        "premium_report": {
            "report_title": "string",
            "version": "string",
            "sections": [
                {
                    "section_id": "string",
                    "category": "personality|money|relationship|career|health|overall",
                    "title": "string",
                    "headline": "string",
                    "summary_lines": ["string", "string", "string"],
                    "core_insight": "string",
                    "patterns": ["string", "string", "string"],
                    "strength": "string",
                    "risk": "string",
                    "action_points": ["string", "string", "string"],
                    "action_note": "string",
                }
            ],
        }
    }
    template = _resolve_prompt_template(prompt_template)
    schema_json = json.dumps(schema, ensure_ascii=False)
    context_json = json.dumps(context, ensure_ascii=False)

    rendered = template.replace("{{SCHEMA_JSON}}", schema_json).replace("{{INPUT_JSON}}", context_json)
    if "{{INPUT_JSON}}" not in template:
        rendered = f"{rendered}\n\n입력 데이터:\n{context_json}"
    return rendered


def _extract_output_text(response_data: dict[str, Any]) -> str:
    top_text = response_data.get("output_text")
    if isinstance(top_text, str) and top_text.strip():
        return top_text.strip()
    if isinstance(top_text, dict):
        top_value = top_text.get("value") or top_text.get("text")
        if isinstance(top_value, str) and top_value.strip():
            return top_value.strip()

    texts: list[str] = []

    def collect(node: Any) -> None:
        if isinstance(node, str):
            value = node.strip()
            if value:
                texts.append(value)
            return
        if not isinstance(node, (dict, list)):
            return

        if isinstance(node, list):
            for item in node:
                collect(item)
            return

        node_type = node.get("type")
        if node_type in {"output_text", "text"}:
            text_value = node.get("text")
            if isinstance(text_value, str):
                collect(text_value)
            elif isinstance(text_value, dict):
                collect(text_value.get("value") or text_value.get("text"))

        refusal = node.get("refusal")
        if isinstance(refusal, str) and refusal.strip():
            collect(refusal)

        raw_text = node.get("text")
        if isinstance(raw_text, dict):
            collect(raw_text.get("value") or raw_text.get("text"))
        elif isinstance(raw_text, str):
            collect(raw_text)

        for key in ("output_text", "message", "content", "output", "items"):
            if key in node:
                collect(node.get(key))

    collect(response_data.get("output"))
    if not texts:
        collect(response_data.get("message"))
    return "\n".join(texts).strip()


def _json_loads_relaxed(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        pass

    sanitized = "".join(ch for ch in text if ch in ("\n", "\r", "\t") or ord(ch) >= 32)
    return json.loads(sanitized, strict=False)


def _extract_first_json_object_candidate(text: str) -> str:
    decoder = json.JSONDecoder(strict=False)
    for start in (idx for idx, ch in enumerate(text) if ch == "{"):
        try:
            obj, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return text[start:end]
    raise RuntimeError("AI 응답에서 JSON 객체를 찾지 못했습니다.")


def _extract_json_object_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        parsed = _json_loads_relaxed(text)
        if isinstance(parsed, dict):
            return text
    except json.JSONDecodeError:
        pass

    candidate = _extract_first_json_object_candidate(text)
    _json_loads_relaxed(candidate)
    return candidate


def _normalize_report(report: dict[str, Any]) -> dict[str, Any]:
    sections_raw = report.get("sections")
    if not isinstance(sections_raw, list):
        sections_raw = []

    normalized_sections: list[dict[str, Any]] = []
    for idx, section in enumerate(sections_raw, start=1):
        if not isinstance(section, dict):
            continue
        normalized_sections.append(
            {
                "section_id": str(section.get("section_id") or f"section_{idx:02d}"),
                "category": str(section.get("category") or "overall"),
                "title": str(section.get("title") or f"섹션 {idx}"),
                "headline": str(section.get("headline") or ""),
                "summary_lines": [str(x).strip() for x in section.get("summary_lines", []) if str(x).strip()],
                "core_insight": str(section.get("core_insight") or ""),
                "strength": str(section.get("strength") or ""),
                "risk": str(section.get("risk") or ""),
                "action_points": [str(x).strip() for x in section.get("action_points", []) if str(x).strip()],
                "action_note": str(section.get("action_note") or ""),
            }
        )

    return {
        "report_title": str(report.get("report_title") or "유료 사주풀이 리포트"),
        "version": str(report.get("version") or "ai-v1"),
        "sections": normalized_sections,
    }


def generate_premium_report_with_ai(
    context: dict[str, Any],
    *,
    model: str | None = None,
    timeout_seconds: int | None = None,
    prompt_template: str | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

    resolved_model = _resolve_model(model)
    resolved_timeout = _resolve_timeout_seconds(timeout_seconds)
    retry_count = _resolve_retry_count()
    base_max_output_tokens = _resolve_max_output_tokens()
    max_output_retry_steps = _resolve_max_output_retry_steps()
    max_output_tokens_cap = _resolve_max_output_tokens_cap(base_max_output_tokens)
    resolved_system_prompt = system_prompt.strip() if isinstance(system_prompt, str) and system_prompt.strip() else SYSTEM_PROMPT
    debug_dir = _resolve_debug_dump_dir()

    user_prompt = _build_user_prompt(context, prompt_template=prompt_template)
    _dump_debug_json(
        debug_dir,
        "request_context",
        {
            "context": context,
            "model": resolved_model,
            "timeout_seconds": resolved_timeout,
            "retry_count": retry_count,
            "max_output_tokens": base_max_output_tokens,
            "max_output_retry_steps": max_output_retry_steps,
            "max_output_tokens_cap": max_output_tokens_cap,
        },
    )
    _dump_debug_json(
        debug_dir,
        "resolved_prompts",
        {
            "system_prompt": resolved_system_prompt,
            "user_prompt": user_prompt,
            "prompt_source": "payload.prompt_text" if isinstance(prompt_template, str) and prompt_template.strip() else "file_or_default",
            "prompt_file": os.getenv("OPENAI_PREMIUM_PROMPT_FILE", "").strip() or DEFAULT_PROMPT_TEMPLATE_PATH,
        },
    )
    max_output_tokens = base_max_output_tokens

    for token_attempt in range(max_output_retry_steps + 1):
        request_body = {
            "model": resolved_model,
            "max_output_tokens": max_output_tokens,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": resolved_system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
        }
        _dump_debug_json(debug_dir, f"request_body_attempt_{token_attempt + 1}", request_body)

        response_data = _request_openai_responses_api(
            api_key=api_key,
            request_body=request_body,
            timeout_seconds=resolved_timeout,
            retry_count=retry_count,
        )
        _dump_debug_json(debug_dir, f"response_attempt_{token_attempt + 1}", response_data)
        output_text = _extract_output_text(response_data)
        max_output_incomplete = _is_max_output_incomplete(response_data)
        _dump_debug_json(
            debug_dir,
            f"output_text_attempt_{token_attempt + 1}",
            {
                "output_text": output_text,
                "status": response_data.get("status"),
                "incomplete_details": response_data.get("incomplete_details"),
                "error": response_data.get("error"),
            },
        )

        if not output_text:
            if max_output_incomplete and token_attempt < max_output_retry_steps and max_output_tokens < max_output_tokens_cap:
                max_output_tokens = min(max_output_tokens * 2, max_output_tokens_cap)
                continue
            status = response_data.get("status")
            incomplete = response_data.get("incomplete_details")
            error = response_data.get("error")
            raise RuntimeError(
                f"AI 응답 텍스트가 비어 있습니다. status={status}, incomplete={incomplete}, error={error}"
            )

        parse_error: Exception | None = None
        parsed: Any = None
        try:
            json_text = _extract_json_object_text(output_text)
            parsed = _json_loads_relaxed(json_text)
        except Exception as exc:  # noqa: BLE001 - keep details for runtime debugging
            parse_error = exc

        if parse_error is not None:
            if max_output_incomplete and token_attempt < max_output_retry_steps and max_output_tokens < max_output_tokens_cap:
                max_output_tokens = min(max_output_tokens * 2, max_output_tokens_cap)
                continue
            raise RuntimeError(f"AI 응답 JSON 파싱 실패: {parse_error}") from parse_error

        report = parsed.get("premium_report") if isinstance(parsed, dict) and "premium_report" in parsed else parsed
        if not isinstance(report, dict):
            if max_output_incomplete and token_attempt < max_output_retry_steps and max_output_tokens < max_output_tokens_cap:
                max_output_tokens = min(max_output_tokens * 2, max_output_tokens_cap)
                continue
            raise RuntimeError("AI 응답에서 premium_report 객체를 찾지 못했습니다.")

        normalized = _normalize_report(report)
        if normalized["sections"]:
            _dump_debug_json(debug_dir, f"normalized_report_attempt_{token_attempt + 1}", {"premium_report": normalized})
            return normalized

        if max_output_incomplete and token_attempt < max_output_retry_steps and max_output_tokens < max_output_tokens_cap:
            max_output_tokens = min(max_output_tokens * 2, max_output_tokens_cap)
            continue
        raise RuntimeError("AI 응답에 유효한 sections가 없습니다.")

    raise RuntimeError("AI 응답 생성에 실패했습니다. max_output_tokens 한도를 확인해 주세요.")
