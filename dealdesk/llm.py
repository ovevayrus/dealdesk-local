"""Adapter for a locally hosted, OpenAI-compatible chat endpoint (Ollama, LM Studio, vLLM, NIM, ...).

There is no cloud fallback: non-local hosts are refused by configuration, and when
the local model fails the agent uses its deterministic, labeled scripted wording.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from typing import Any

from .config import Settings


class LocalModelError(RuntimeError):
    pass


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """The host allowlist is checked once, so a redirect must not move the request elsewhere."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LocalModelError("Local model endpoint redirected; redirects are refused.")


# No system proxies (a proxy could forward requests off the machine) and no redirects.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _RefuseRedirects())
MAX_RESPONSE_BYTES = 1_048_576
_SLOTS = threading.BoundedSemaphore(2)


def _request(settings: Settings, method: str, path: str, body: dict[str, Any] | None = None,
             timeout: float | None = None) -> dict[str, Any]:
    error = settings.llm_endpoint_error()
    if error:
        raise LocalModelError(error)
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(f"{settings.llm_base_url}{path}", data=data, headers=headers, method=method)
    if not _SLOTS.acquire(blocking=False):
        raise LocalModelError("Local model is busy; at most two requests may run at once.")
    try:
        with _OPENER.open(request, timeout=timeout or settings.llm_timeout_seconds) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise LocalModelError("Local model response exceeded 1 MiB.")
            result = json.loads(raw.decode("utf-8"))
            if not isinstance(result, dict):
                raise LocalModelError("Local model returned a non-object response.")
            return result
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LocalModelError(f"Local model request failed ({type(exc).__name__}).") from exc
    finally:
        _SLOTS.release()


def model_status(settings: Settings) -> dict[str, Any]:
    if settings.mode != "local_model":
        return {"reachable": None, "detail": "Scripted demo mode: no model is called."}
    error = settings.llm_endpoint_error()
    if error:
        return {"reachable": False, "detail": error}
    try:
        listing = _request(settings, "GET", "/models", timeout=3)
    except LocalModelError as exc:
        return {"reachable": False, "detail": str(exc)}
    names = [item.get("id") for item in listing.get("data", []) if isinstance(item, dict)]
    found = settings.llm_model in names if names else None
    detail = "Model listed by endpoint." if found else (
        "Endpoint reachable; configured model not listed." if names else "Endpoint reachable.")
    return {"reachable": True, "model_listed": found, "detail": detail}


def chat(settings: Settings, system: str, user: str, max_tokens: int = 350) -> str:
    response = _request(settings, "POST", "/chat/completions", {
        "model": settings.llm_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "stream": False,
        # Reasoning models (e.g. Qwen3 on vLLM) otherwise spend the token budget thinking and return no content.
        "chat_template_kwargs": {"enable_thinking": False},
    })
    try:
        text = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LocalModelError("Local model returned an unexpected response shape.") from exc
    if isinstance(text, str):
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)  # reasoning-model scratchpad
    if not isinstance(text, str) or not text.strip():
        raise LocalModelError("Local model returned an empty response.")
    return text.strip()
