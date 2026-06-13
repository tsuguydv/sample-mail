"""Validation and sanitization for user-defined email templates."""
from __future__ import annotations

import json
import re
from typing import Any

from app.email_builder.registry import BLOCK_REGISTRY

MAX_USER_TEMPLATES_PER_USER = 50
MAX_BLOCKS_IN_LAYOUT = 40
MAX_CONTEXT_STRING_LEN = 8000
MAX_CONTEXT_URL_LEN = 2048
MAX_LAYOUT_JSON_BYTES = 512_000
MAX_PREVIEW_BODY_HTML = 100_000
MAX_TEMPLATE_NAME_LEN = 200
MAX_SUBJECT_LEN = 500

ALLOWED_THEME_KEYS = frozenset({"primary", "secondary", "accent", "surface", "colorScheme"})
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
URL_KEY_HINTS = ("url", "link", "href", "website")
SAFE_URL_PREFIXES = ("http://", "https://", "mailto:", "data:image/")


class TemplateValidationError(ValueError):
    pass


def sanitize_string(value: Any, *, max_len: int = MAX_CONTEXT_STRING_LEN) -> str:
    if value is None:
        return ""
    text = str(value)
    if len(text) > max_len:
        text = text[:max_len]
    return text


def sanitize_url(value: Any) -> str:
    url = sanitize_string(value, max_len=MAX_CONTEXT_URL_LEN).strip()
    if not url or url == "#":
        return url or "#"
    lower = url.lower()
    if lower.startswith(SAFE_URL_PREFIXES):
        return url
    if url.startswith("#"):
        return url
    return "#"


def _is_url_field(key: str) -> bool:
    k = (key or "").lower()
    return any(h in k for h in URL_KEY_HINTS)


def sanitize_context_value(key: str, value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return sanitize_url(value) if _is_url_field(key) else sanitize_string(value)
    if isinstance(value, list):
        if not value:
            return []
        if isinstance(value[0], str):
            return [sanitize_string(v, max_len=4000) for v in value[:20]]
        return []
    if isinstance(value, dict):
        return {}
    return ""


def validate_block_layout(layout: list | None) -> list[dict]:
    if not isinstance(layout, list):
        raise TemplateValidationError("Invalid block layout")
    raw = json.dumps(layout, ensure_ascii=False)
    if len(raw.encode("utf-8")) > MAX_LAYOUT_JSON_BYTES:
        raise TemplateValidationError("Template layout is too large")
    if len(layout) > MAX_BLOCKS_IN_LAYOUT:
        raise TemplateValidationError(f"Too many blocks (max {MAX_BLOCKS_IN_LAYOUT})")
    if not layout:
        raise TemplateValidationError("Layout must contain at least one block")

    out: list[dict] = []
    for item in layout:
        if not isinstance(item, dict):
            raise TemplateValidationError("Invalid block entry")
        name = str(item.get("name") or "").strip()
        if name not in BLOCK_REGISTRY:
            raise TemplateValidationError(f"Unknown block type: {name}")
        ctx = item.get("context")
        if ctx is not None and not isinstance(ctx, dict):
            raise TemplateValidationError("Invalid block context")
        clean_ctx: dict[str, Any] = {}
        for k, v in (ctx or {}).items():
            if not isinstance(k, str) or not k.strip() or len(k) > 64:
                continue
            clean_ctx[k.strip()] = sanitize_context_value(k, v)
        out.append({"name": name, "context": clean_ctx})
    return out


def sanitize_theme(theme: dict | None) -> dict:
    if not isinstance(theme, dict):
        return {}
    out: dict[str, str] = {}
    for key in ALLOWED_THEME_KEYS:
        if key not in theme:
            continue
        val = str(theme.get(key) or "").strip()
        if key == "colorScheme" and val in ("light", "dark", "brand"):
            out[key] = val
        elif key != "colorScheme" and HEX_COLOR_RE.match(val):
            out[key] = val
    return out


def sanitize_template_name(name: str) -> str:
    cleaned = sanitize_string(name, max_len=MAX_TEMPLATE_NAME_LEN).strip()
    if not cleaned:
        raise TemplateValidationError("Template name is required")
    return cleaned


def sanitize_preview_subject(subject: str) -> str:
    return sanitize_string(subject, max_len=MAX_SUBJECT_LEN).strip() or "Preview"


def sanitize_preview_body_html(html: str) -> str:
    return sanitize_string(html, max_len=MAX_PREVIEW_BODY_HTML)
