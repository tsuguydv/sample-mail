"""
GigaChat (Sber) API client: OAuth token caching, text chat completion, text2image.

Auth: POST {GIGACHAT_OAUTH_URL} with `Authorization: Basic <GIGACHAT_AUTH_KEY>` and a
`RqUID` header, body `scope=<GIGACHAT_SCOPE>`. The access token lives ~30 minutes.
Text and images use the OpenAI-compatible {GIGACHAT_BASE_URL}/chat/completions endpoint.

Trial individual ("физлицо") accounts usually do not have the Минцифры root cert
installed, so `GIGACHAT_VERIFY_SSL` defaults to False for testing.
"""

from __future__ import annotations

import re
import threading
import time
import uuid

import httpx

from app.config import (
    GIGACHAT_AUTH_KEY,
    GIGACHAT_SCOPE,
    GIGACHAT_MODEL,
    GIGACHAT_OAUTH_URL,
    GIGACHAT_BASE_URL,
    GIGACHAT_VERIFY_SSL,
)

# Cached OAuth token shared across threads (generation runs in asyncio.to_thread).
_token_lock = threading.Lock()
_access_token: str | None = None
_token_expires_at: float = 0.0  # unix seconds

_IMG_SRC_RE = re.compile(r'<img[^>]*\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)


def is_configured() -> bool:
    return bool(GIGACHAT_AUTH_KEY)


def _get_access_token() -> str:
    """Return a valid access token, refreshing ~60s before expiry. Thread-safe."""
    global _access_token, _token_expires_at
    now = time.time()
    with _token_lock:
        if _access_token and now < (_token_expires_at - 60):
            return _access_token
        if not GIGACHAT_AUTH_KEY:
            raise RuntimeError("GIGACHAT_AUTH_KEY is not set")
        resp = httpx.post(
            GIGACHAT_OAUTH_URL,
            headers={
                "Authorization": f"Basic {GIGACHAT_AUTH_KEY}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"scope": GIGACHAT_SCOPE},
            verify=GIGACHAT_VERIFY_SSL,
            timeout=30.0,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"GigaChat OAuth failed: {resp.status_code} {resp.text[:300]}")
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("GigaChat OAuth returned no access_token")
        # expires_at is a unix timestamp in milliseconds; fall back to +25 min.
        exp_ms = data.get("expires_at")
        if isinstance(exp_ms, (int, float)) and exp_ms > 0:
            _token_expires_at = float(exp_ms) / 1000.0
        else:
            _token_expires_at = now + 25 * 60
        _access_token = token
        return token


def _auth_headers(extra: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def chat_completion(messages: list[dict], temperature: float = 0.3) -> str:
    """Send a chat completion request and return the assistant message content as a string."""
    resp = httpx.post(
        f"{GIGACHAT_BASE_URL}/chat/completions",
        headers=_auth_headers(),
        json={
            "model": GIGACHAT_MODEL,
            "messages": messages,
            "temperature": temperature,
        },
        verify=GIGACHAT_VERIFY_SSL,
        timeout=120.0,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"GigaChat chat failed: {resp.status_code} {resp.text[:300]}")
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    msg = (choices[0] or {}).get("message") or {}
    content = msg.get("content")
    return content if isinstance(content, str) else str(content or "")


def generate_image_bytes(prompt: str) -> bytes | None:
    """
    Ask GigaChat to draw an image (built-in text2image via function_call) and download it.
    Returns JPEG bytes, or None if the model did not produce an image.
    """
    resp = httpx.post(
        f"{GIGACHAT_BASE_URL}/chat/completions",
        headers=_auth_headers(),
        json={
            "model": GIGACHAT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты — художник. Когда пользователь описывает изображение, нарисуй его.",
                },
                {"role": "user", "content": prompt},
            ],
            "function_call": "auto",
        },
        verify=GIGACHAT_VERIFY_SSL,
        timeout=180.0,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"GigaChat image request failed: {resp.status_code} {resp.text[:300]}")
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return None
    content = ((choices[0] or {}).get("message") or {}).get("content") or ""
    match = _IMG_SRC_RE.search(content if isinstance(content, str) else "")
    if not match:
        return None
    file_id = match.group(1).strip()
    if not file_id:
        return None
    file_resp = httpx.get(
        f"{GIGACHAT_BASE_URL}/files/{file_id}/content",
        headers={
            "Authorization": f"Bearer {_get_access_token()}",
            "Accept": "application/jpg",
        },
        verify=GIGACHAT_VERIFY_SSL,
        timeout=120.0,
    )
    if file_resp.status_code >= 400 or not file_resp.content:
        return None
    return file_resp.content
