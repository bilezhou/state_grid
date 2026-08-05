from __future__ import annotations

import re
from typing import Any

LOGIN_ERROR_FALLBACK = "登录失败，请检查账号密码"
_WRAPPER_FAILURE_CODES = {1, "1"}
_SENSITIVE_ERROR_PATTERNS = (
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "<redacted phone>"),
    (re.compile(r"(?<!\d)\d{13,}(?!\d)"), "<redacted number>"),
)


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _redact_error_detail(value: Any) -> str:
    detail = str(value)
    for pattern, replacement in _SENSITIVE_ERROR_PATTERNS:
        detail = pattern.sub(replacement, detail)
    return " ".join(detail.split())[:500]


def build_login_error_result(response: Any, fallback_message: Any = None) -> dict[str, Any]:
    """Wrap a failed login response without discarding its upstream error code."""
    response_dict = response if isinstance(response, dict) else {}
    data = response_dict.get("data")
    data_dict = data if isinstance(data, dict) else {}
    service = data_dict.get("srvrt")
    service_dict = service if isinstance(service, dict) else {}

    original_code = service_dict.get("resultCode")
    if not _present(original_code):
        original_code = service_dict.get("code")
    if not _present(original_code):
        original_code = response_dict.get("resultCode")
    if not _present(original_code):
        top_level_code = response_dict.get("code")
        if top_level_code not in _WRAPPER_FAILURE_CODES and _present(top_level_code):
            original_code = top_level_code

    message = (
        service_dict.get("resultMessage")
        or service_dict.get("errmsg")
        or service_dict.get("message")
        or response_dict.get("errmsg")
        or response_dict.get("message")
        or response_dict.get("msg")
        or fallback_message
    )

    result: dict[str, Any] = {"errcode": 1}
    if _present(original_code):
        result["original_code"] = original_code
    if _present(message):
        result["errmsg"] = message
    return result


def format_login_error(result: Any) -> str:
    """Format login failures while suppressing the uninformative wrapper errcode=1."""
    if not isinstance(result, dict):
        return LOGIN_ERROR_FALLBACK

    original_code = result.get("original_code")
    if not _present(original_code):
        original_code = result.get("resultCode")
    if not _present(original_code):
        direct_code = result.get("code")
        if direct_code not in _WRAPPER_FAILURE_CODES and _present(direct_code):
            original_code = direct_code

    parts: list[str] = []
    if _present(original_code):
        parts.append(f"code={original_code}")
    else:
        wrapper_code = result.get("errcode")
        if wrapper_code not in _WRAPPER_FAILURE_CODES and _present(wrapper_code):
            parts.append(f"errcode={wrapper_code}")

    message = result.get("errmsg") or result.get("message") or result.get("msg")
    if _present(message):
        parts.append(_redact_error_detail(message))

    return "，".join(parts) if parts else LOGIN_ERROR_FALLBACK
