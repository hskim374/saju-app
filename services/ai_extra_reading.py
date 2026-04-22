"""OpenAI-based extra reading generator (category/question story cards)."""

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
DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_RETRY_COUNT = 1
DEFAULT_MAX_OUTPUT_TOKENS = 4000
DEFAULT_PROMPT_PATH = "data/prompts/extra_reading_prompt.txt"
DEFAULT_DEBUG_DUMP_DIR = "logs/ai_extra_reading"
DEBUG_LOG_RETENTION_DAYS = 2
DEFAULT_SYSTEM_PROMPT = (
    "너는 한국어 생활형 사주 해석 작성기다. "
    "입력 context와 선택한 카테고리/질문만 근거로 extra_reading JSON 객체만 반환한다. "
    "마크다운, 코드블록, 설명문 없이 JSON만 출력한다."
)
DEFAULT_BUNDLE_SYSTEM_PROMPT = (
    "너는 한국어 생활형 사주 해석 작성기다. "
    "입력된 카테고리, 질문 목록, 사주 핵심 풀이를 근거로 extra_reading_bundle JSON 객체만 반환한다. "
    "마크다운, 코드블록, 설명문 없이 JSON만 출력한다."
)


def _resolve_model() -> str:
    return os.getenv("OPENAI_EXTRA_READING_MODEL", "").strip() or os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_MODEL


def _resolve_timeout() -> int:
    raw = os.getenv("OPENAI_EXTRA_READING_TIMEOUT_SECONDS", "").strip() or os.getenv("OPENAI_TIMEOUT_SECONDS", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return DEFAULT_TIMEOUT_SECONDS


def _resolve_retry_count() -> int:
    raw = os.getenv("OPENAI_EXTRA_READING_RETRY_COUNT", "").strip() or os.getenv("OPENAI_RETRY_COUNT", "").strip()
    if raw.isdigit():
        return max(0, int(raw))
    return DEFAULT_RETRY_COUNT


def _resolve_max_tokens() -> int:
    raw = os.getenv("OPENAI_EXTRA_READING_MAX_OUTPUT_TOKENS", "").strip() or os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return DEFAULT_MAX_OUTPUT_TOKENS


def _resolve_prompt_template() -> str:
    prompt_path = os.getenv("OPENAI_EXTRA_READING_PROMPT_FILE", "").strip() or DEFAULT_PROMPT_PATH
    try:
        text = open(prompt_path, "r", encoding="utf-8").read().strip()
        if text:
            return text
    except OSError:
        pass
    return (
        "다음 입력 데이터로 extra_reading JSON을 생성해라.\n"
        "출력은 JSON 객체 하나만 허용.\n\n"
        "{{INPUT_JSON}}"
    )


def _resolve_debug_dump_dir() -> Path | None:
    raw_dir = os.getenv("OPENAI_EXTRA_READING_DEBUG_DIR", "").strip()
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


def _extract_output_text(response_data: dict[str, Any]) -> str:
    top = response_data.get("output_text")
    if isinstance(top, str) and top.strip():
        return top.strip()
    if isinstance(top, dict):
        val = top.get("value") or top.get("text")
        if isinstance(val, str) and val.strip():
            return val.strip()

    texts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            if node.strip():
                texts.append(node.strip())
            return
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        if isinstance(node.get("text"), str):
            walk(node.get("text"))
        if isinstance(node.get("text"), dict):
            walk(node.get("text", {}).get("value") or node.get("text", {}).get("text"))
        for key in ("output_text", "output", "content", "message", "items", "refusal"):
            if key in node:
                walk(node.get(key))

    walk(response_data.get("output"))
    if not texts:
        walk(response_data.get("message"))
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


def _is_timeout_like_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return True
        if isinstance(reason, str) and "timed out" in reason.lower():
            return True
    return "timed out" in str(exc).lower()


def _is_retryable_http_status(status_code: int) -> bool:
    return status_code in {408, 409, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}


def _retry_after_seconds(headers: Any) -> float:
    if headers is None:
        return 0.0
    try:
        raw = headers.get("Retry-After")
    except Exception:
        raw = None
    if raw is None:
        return 0.0
    text = str(raw).strip()
    if not text.isdigit():
        return 0.0
    return float(max(0, int(text)))


def _compute_retry_sleep(attempt: int, retry_after: float = 0.0) -> float:
    backoff = min(6.0, 0.6 * float(attempt + 1) * 2.0)
    return max(backoff, retry_after)


def _normalize_extra_reading(extra: dict[str, Any]) -> dict[str, Any]:
    def to_lines(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        text = str(value or "").strip()
        return [text] if text else []

    normalized = {
        "category": str(extra.get("category") or ""),
        "question": str(extra.get("question") or ""),
        "title": str(extra.get("title") or "추가 사주보기"),
        "headline": str(extra.get("headline") or ""),
        "story": to_lines(extra.get("story")),
        "warnings": to_lines(extra.get("warnings")),
        "tips": to_lines(extra.get("tips")),
        "closing": str(extra.get("closing") or ""),
    }
    if not normalized["story"] and normalized["headline"]:
        normalized["story"] = [normalized["headline"]]
    return normalized


def _normalize_extra_reading_bundle(
    *,
    source: dict[str, Any],
    category_label: str,
    questions: list[str],
) -> dict[str, Any]:
    items_raw = source.get("items")
    if not isinstance(items_raw, list):
        items_raw = []

    normalized_items: list[dict[str, Any]] = []
    for idx, question in enumerate(questions):
        raw_item = items_raw[idx] if idx < len(items_raw) and isinstance(items_raw[idx], dict) else {}
        item = _normalize_extra_reading(
            {
                "category": str(raw_item.get("category") or source.get("category") or category_label),
                "question": str(raw_item.get("question") or question),
                "title": str(raw_item.get("title") or f"{category_label} #{idx + 1}"),
                "headline": str(raw_item.get("headline") or ""),
                "story": raw_item.get("story"),
                "warnings": raw_item.get("warnings"),
                "tips": raw_item.get("tips"),
                "closing": str(raw_item.get("closing") or ""),
            }
        )
        if not item["headline"]:
            item["headline"] = f"{question} 관점에서 지금은 기준을 먼저 정하면 흐름이 안정되기 쉽습니다."
        normalized_items.append(item)

    return {
        "category": str(source.get("category") or category_label),
        "title": str(source.get("title") or f"{category_label} 추가 사주보기"),
        "items": normalized_items,
    }


def _request_openai_response(*, api_key: str, body: dict[str, Any], timeout_seconds: int, retry_count: int) -> dict[str, Any]:
    req = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    raw_text = ""
    last_timeout_error: BaseException | None = None
    for attempt in range(retry_count + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                raw_text = response.read().decode("utf-8")
            last_timeout_error = None
            break
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="ignore")
            if _is_retryable_http_status(exc.code) and attempt < retry_count:
                time.sleep(_compute_retry_sleep(attempt, _retry_after_seconds(getattr(exc, "headers", None))))
                continue
            raise RuntimeError(f"OpenAI API 요청 실패 ({exc.code}): {err}") from exc
        except urllib.error.URLError as exc:
            if _is_timeout_like_error(exc):
                last_timeout_error = exc
                if attempt < retry_count:
                    time.sleep(_compute_retry_sleep(attempt))
                    continue
                break
            raise RuntimeError(f"OpenAI API 연결 실패: {exc.reason}") from exc
        except (TimeoutError, socket.timeout) as exc:
            last_timeout_error = exc
            if attempt < retry_count:
                time.sleep(_compute_retry_sleep(attempt))
                continue
            break

    if last_timeout_error is not None:
        raise RuntimeError(f"OpenAI API 응답 시간 초과 ({timeout_seconds}초)")

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI API 응답이 JSON 형식이 아닙니다.") from exc


def generate_extra_reading_with_ai(
    *,
    context: dict[str, Any],
    category_label: str,
    question: str,
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

    model = _resolve_model()
    timeout_seconds = _resolve_timeout()
    retry_count = _resolve_retry_count()
    max_tokens = _resolve_max_tokens()
    template = _resolve_prompt_template()
    system_prompt = os.getenv("OPENAI_EXTRA_READING_SYSTEM_PROMPT", "").strip() or DEFAULT_SYSTEM_PROMPT

    payload_for_prompt = {
        "category": category_label,
        "question": question,
        "context": context,
        "output_schema": {
            "extra_reading": {
                "category": "string",
                "question": "string",
                "title": "string",
                "headline": "string",
                "story": ["string"],
                "warnings": ["string"],
                "tips": ["string"],
                "closing": "string",
            }
        },
    }
    user_prompt = template.replace("{{INPUT_JSON}}", json.dumps(payload_for_prompt, ensure_ascii=False))
    body = {
        "model": model,
        "max_output_tokens": max_tokens,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
    }
    response_data = _request_openai_response(
        api_key=api_key,
        body=body,
        timeout_seconds=timeout_seconds,
        retry_count=retry_count,
    )

    output_text = _extract_output_text(response_data)
    if not output_text:
        raise RuntimeError(
            f"AI 응답 텍스트가 비어 있습니다. status={response_data.get('status')}, "
            f"incomplete={response_data.get('incomplete_details')}, error={response_data.get('error')}"
        )

    json_text = _extract_json_object_text(output_text)
    parsed = _json_loads_relaxed(json_text)
    source = parsed.get("extra_reading") if isinstance(parsed, dict) and "extra_reading" in parsed else parsed
    if not isinstance(source, dict):
        raise RuntimeError("AI 응답에서 extra_reading 객체를 찾지 못했습니다.")
    normalized = _normalize_extra_reading(source)
    if not normalized["headline"]:
        raise RuntimeError("AI 응답에서 extra_reading.headline이 비어 있습니다.")
    return normalized


def generate_extra_reading_bundle_with_ai(
    *,
    context: dict[str, Any],
    category_label: str,
    questions: list[str],
    core_insight: str = "",
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

    cleaned_questions = [str(q).strip() for q in questions if str(q).strip()]
    if not cleaned_questions:
        raise RuntimeError("질문 목록이 비어 있어 추가 사주보기를 생성할 수 없습니다.")

    model = _resolve_model()
    timeout_seconds = _resolve_timeout()
    retry_count = _resolve_retry_count()
    max_tokens = _resolve_max_tokens()
    system_prompt = os.getenv("OPENAI_EXTRA_READING_BUNDLE_SYSTEM_PROMPT", "").strip() or DEFAULT_BUNDLE_SYSTEM_PROMPT
    debug_dir = _resolve_debug_dump_dir()

    payload_for_prompt = {
        "category": category_label,
        "questions": cleaned_questions,
        "core_insight": str(core_insight or ""),
        "context": context,
        "output_schema": {
            "extra_reading_bundle": {
                "category": "string",
                "title": "string",
                "items": [
                    {
                        "category": "string",
                        "question": "string",
                        "title": "string",
                        "headline": "string",
                        "story": ["string"],
                        "warnings": ["string"],
                        "tips": ["string"],
                        "closing": "string",
                    }
                ],
            }
        },
    }

    user_prompt = (
        "다음 입력으로 extra_reading_bundle JSON 객체만 생성하라.\n"
        "- questions의 순서를 그대로 유지해 items를 만든다.\n"
        "- items 개수는 questions 개수와 반드시 같아야 한다.\n"
        "- story는 각 항목 3~5문장, warnings 1~2문장, tips 2~3문장, closing 1문장.\n"
        "- patterns 필드는 절대 출력하지 않는다.\n"
        "- 생활언어로 작성한다.\n\n"
        + json.dumps(payload_for_prompt, ensure_ascii=False)
    )

    body = {
        "model": model,
        "max_output_tokens": max_tokens,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
    }
    _dump_debug_json(
        debug_dir,
        "bundle_request_context",
        {
            "category": category_label,
            "questions": cleaned_questions,
            "core_insight": str(core_insight or ""),
            "context": context,
            "model": model,
            "timeout_seconds": timeout_seconds,
            "retry_count": retry_count,
            "max_output_tokens": max_tokens,
        },
    )
    _dump_debug_json(
        debug_dir,
        "bundle_resolved_prompts",
        {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        },
    )
    _dump_debug_json(debug_dir, "bundle_request_body_attempt_1", body)

    response_data = _request_openai_response(
        api_key=api_key,
        body=body,
        timeout_seconds=timeout_seconds,
        retry_count=retry_count,
    )
    _dump_debug_json(debug_dir, "bundle_response_attempt_1", response_data)
    output_text = _extract_output_text(response_data)
    _dump_debug_json(
        debug_dir,
        "bundle_output_text_attempt_1",
        {
            "output_text": output_text,
            "status": response_data.get("status"),
            "incomplete_details": response_data.get("incomplete_details"),
            "error": response_data.get("error"),
        },
    )
    if not output_text:
        raise RuntimeError(
            f"AI 응답 텍스트가 비어 있습니다. status={response_data.get('status')}, "
            f"incomplete={response_data.get('incomplete_details')}, error={response_data.get('error')}"
        )

    json_text = _extract_json_object_text(output_text)
    parsed = _json_loads_relaxed(json_text)
    source = (
        parsed.get("extra_reading_bundle")
        if isinstance(parsed, dict) and "extra_reading_bundle" in parsed
        else parsed
    )
    if not isinstance(source, dict):
        raise RuntimeError("AI 응답에서 extra_reading_bundle 객체를 찾지 못했습니다.")

    normalized = _normalize_extra_reading_bundle(
        source=source,
        category_label=category_label,
        questions=cleaned_questions,
    )
    _dump_debug_json(debug_dir, "bundle_normalized_result_attempt_1", {"extra_reading_bundle": normalized})
    return normalized
