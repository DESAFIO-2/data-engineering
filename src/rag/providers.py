"""Adaptadores LangChain para Gemini; chave e modelos vêm do .env."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

from pydantic import SecretStr

_PERMANENT_QUOTA_RE = re.compile(
    r"per day limit exceeded|daily quota|requests per day",
    re.IGNORECASE,
)
_TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_TRANSIENT_NAME_RE = re.compile(
    r"RateLimit|ResourceExhausted|ServiceUnavailable|TooManyRequests|"
    r"InternalServerError|APIConnection|Timeout",
    re.IGNORECASE,
)
_TRANSIENT_MSG_RE = re.compile(
    r"\b(?:429|500|502|503|504)\b|resource_exhausted|rate[ _-]?limit|"
    r"too many requests|temporarily unavailable|service unavailable|timed out",
    re.IGNORECASE,
)


def _exception_chain(exc: Exception) -> list[BaseException]:
    chain: list[BaseException] = []
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen and len(chain) < 6:
        seen.add(id(cur))
        chain.append(cur)
        cur = cur.__cause__ or cur.__context__
    return chain


def is_transient_provider_error(exc: Exception) -> bool:
    """Return True for transient LLM/HTTP failures worth retrying with backoff."""
    chain = _exception_chain(exc)
    full_msg = " ".join(str(item) for item in chain)
    if _PERMANENT_QUOTA_RE.search(full_msg):
        return False
    for item in chain:
        status = getattr(item, "status_code", None)
        if status is None:
            status = getattr(item, "code", None)
        if isinstance(status, int) and status in _TRANSIENT_STATUS_CODES:
            return True
        if _TRANSIENT_NAME_RE.search(type(item).__name__):
            return True
    return bool(_TRANSIENT_MSG_RE.search(full_msg))


def _retry_delay_seconds(
    exc: Exception, attempt: int, *, base_delay: float, max_delay: float
) -> float:
    retry = re.search(r"retry(?: in| after)?[:=\s]+([\d.]+)\s*s?", str(exc), re.I)
    if retry:
        return min(max_delay, max(0.0, float(retry.group(1))))
    return float(min(max_delay, base_delay * (2**attempt)))


def invoke_with_retry(
    llm: Any,
    messages: Any,
    *,
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    sleep: Callable[[float], None] | None = None,
) -> Any:
    """Invoke an LLM adapter with exponential backoff on transient 429/5xx errors."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if getattr(llm, "_handles_retries", False):
        return llm.invoke(messages)
    sleep_fn = sleep or time.sleep
    for attempt in range(max_attempts):
        try:
            return llm.invoke(messages)
        except Exception as exc:
            if attempt + 1 >= max_attempts or not is_transient_provider_error(exc):
                raise
            delay = _retry_delay_seconds(exc, attempt, base_delay=base_delay, max_delay=max_delay)
            if delay > 0:
                sleep_fn(delay)
    raise RuntimeError("Unreachable retry state")


def error_detail(exc: Exception) -> str:
    """Report provider causes without exposing the configured API key."""
    from .config import get_settings

    message = f"{type(exc).__name__}: {exc}"
    if exc.__cause__:
        message += f"; causa: {type(exc.__cause__).__name__}: {exc.__cause__}"
    key = get_settings().google_api_key
    if key:
        message = message.replace(key, "[REDACTED]")
    message = re.sub(r"AIza[\w-]+", "[REDACTED]", message)
    message = re.sub(r"(?i)(key|api_key)=([^&\s]+)", r"\1=[REDACTED]", message)
    return " ".join(message.split())[:1200]


def google_embeddings(model: str, api_key: str) -> Any:
    if not api_key.strip():
        raise ValueError("Preencha APP_GOOGLE_API_KEY em .env")
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=model, api_key=SecretStr(api_key))


def google_chat(model: str, api_key: str) -> Any:
    if not api_key.strip():
        raise ValueError("Preencha APP_GOOGLE_API_KEY em .env")
    from langchain_google_genai import ChatGoogleGenerativeAI

    normalized_model = model.lower().rsplit("/", 1)[-1]
    if normalized_model.startswith(("gemini-3.5-flash-lite", "gemini-3.6-flash")):
        # These models have fixed sampling defaults; passing temperature causes
        # langchain-google-genai to warn and discard it on every generation.
        sampling = {}
    else:
        sampling = {"temperature": 0}
    return ChatGoogleGenerativeAI(
        model=model,
        api_key=SecretStr(api_key),
        timeout=60,
        max_retries=2,
        **sampling,
    )
