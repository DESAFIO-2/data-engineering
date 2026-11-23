"""Adaptadores LangChain para Gemini com suporte a chave principal e fallbacks."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Sequence
from typing import Any, cast

from pydantic import SecretStr

_PERMANENT_QUOTA_RE = re.compile(
    r"per day limit exceeded|daily quota|requests per day",
    re.IGNORECASE,
)
_KEY_AUTH_RE = re.compile(
    r"PermissionDenied|Unauthenticated|Unauthorized|"
    r"api[_ ]?key[_ ]?not[_ ]?valid|api_key_invalid|invalid[_ ]?api[_ ]?key|"
    r"permission[_ ]?denied|unauthenticated|unauthorized|\b(?:401|403)\b",
    re.IGNORECASE,
)
_PERMANENT_KEY_MSG_RE = re.compile(
    r"per day limit exceeded|daily quota|requests per day|"
    r"api[_ ]?key[_ ]?not[_ ]?valid|api_key_invalid|invalid[_ ]?api[_ ]?key|"
    r"permission[_ ]?denied|unauthenticated|unauthorized|\b(?:401|403)\b",
    re.IGNORECASE,
)
_KEY_FAILOVER_NAME_RE = re.compile(
    r"PermissionDenied|Unauthenticated|Unauthorized|RateLimit|ResourceExhausted|TooManyRequests",
    re.IGNORECASE,
)
_KEY_FAILOVER_MSG_RE = re.compile(
    r"per day limit exceeded|daily quota|requests per day|"
    r"api[_ ]?key[_ ]?not[_ ]?valid|api_key_invalid|invalid[_ ]?api[_ ]?key|"
    r"permission[_ ]?denied|unauthenticated|unauthorized|\b(?:401|403|429)\b|"
    r"resource_exhausted|rate[ _-]?limit|too many requests|quota",
    re.IGNORECASE,
)
_TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_KEY_FAILOVER_STATUS_CODES = frozenset({401, 403, 429})
_PERMANENT_KEY_STATUS_CODES = frozenset({401, 403})
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


def _status_code(item: BaseException) -> int | None:
    status = getattr(item, "status_code", None)
    if status is None:
        status = getattr(item, "code", None)
    return status if isinstance(status, int) and not isinstance(status, bool) else None


def _chain_matches(
    exc: Exception,
    *,
    statuses: frozenset[int],
    name_re: re.Pattern[str],
    msg_re: re.Pattern[str],
) -> bool:
    chain = _exception_chain(exc)
    if msg_re.search(" ".join(str(item) for item in chain)):
        return True
    return any(
        _status_code(item) in statuses or bool(name_re.search(type(item).__name__))
        for item in chain
    )


def _is_permanent_key_failure(exc: Exception) -> bool:
    return _chain_matches(
        exc,
        statuses=_PERMANENT_KEY_STATUS_CODES,
        name_re=_KEY_AUTH_RE,
        msg_re=_PERMANENT_KEY_MSG_RE,
    )


def is_transient_provider_error(exc: Exception) -> bool:
    """Return True for transient LLM/HTTP failures worth retrying with backoff."""
    if _is_permanent_key_failure(exc):
        return False
    return _chain_matches(
        exc,
        statuses=_TRANSIENT_STATUS_CODES,
        name_re=_TRANSIENT_NAME_RE,
        msg_re=_TRANSIENT_MSG_RE,
    )


def is_key_failover_error(exc: Exception) -> bool:
    """Return True when switching to a fallback API key can plausibly recover."""
    return _chain_matches(
        exc,
        statuses=_KEY_FAILOVER_STATUS_CODES,
        name_re=_KEY_FAILOVER_NAME_RE,
        msg_re=_KEY_FAILOVER_MSG_RE,
    )


def normalize_api_keys(
    api_key: str | Sequence[str],
    fallback_keys: Sequence[str] = (),
) -> tuple[str, ...]:
    """Normalize primary + fallback API keys into a deduplicated priority tuple."""
    raw_items: list[str] = (
        [api_key, *fallback_keys] if isinstance(api_key, str) else [*api_key, *fallback_keys]
    )
    keys: list[str] = []
    for raw in raw_items:
        cleaned = raw.strip()
        if cleaned and cleaned not in keys:
            keys.append(cleaned)
    if not keys:
        raise ValueError("Preencha APP_GOOGLE_API_KEY em .env")
    return tuple(keys)


class _FailoverPool[T]:
    """Execute calls against ordered key clients with failover on quota/auth failures."""

    def __init__(self, clients: Sequence[T]) -> None:
        if not clients:
            raise ValueError("clients must not be empty")
        self._clients = list(clients)
        self._cursor = 0
        self._exhausted: set[int] = set()

    @property
    def active_index(self) -> int:
        """Index of the client currently prioritized."""
        return self._cursor

    def _candidate_indices(self) -> list[int]:
        total = len(self._clients)
        ordered = [(self._cursor + offset) % total for offset in range(total)]
        available = [idx for idx in ordered if idx not in self._exhausted]
        return available or [self._cursor]

    def execute[R](self, fn: Callable[[T], R]) -> R:
        last_exc: Exception | None = None
        candidates = self._candidate_indices()
        for pos, idx in enumerate(candidates):
            try:
                result = fn(self._clients[idx])
                self._cursor = idx
                return result
            except Exception as exc:
                last_exc = exc
                if _is_permanent_key_failure(exc):
                    self._exhausted.add(idx)
                if not is_key_failover_error(exc) or pos + 1 >= len(candidates):
                    raise
                self._cursor = candidates[pos + 1]
        assert last_exc is not None
        raise last_exc


class _FallbackEmbeddings:
    """Embedding adapter failing over across configured API keys."""

    def __init__(self, clients: Sequence[Any]) -> None:
        self._pool: _FailoverPool[Any] = _FailoverPool(clients)

    @property
    def active_index(self) -> int:
        return self._pool.active_index

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._pool.execute(lambda client: client.embed_documents(texts))

    def embed_query(self, text: str) -> list[float]:
        return self._pool.execute(lambda client: client.embed_query(text))


class CachedQueryEmbeddings:
    """Reuse query vectors during a single evaluation run."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.queries: dict[str, list[float]] = {}

    def embed_query(self, text: str) -> list[float]:
        if text not in self.queries:
            self.queries[text] = self.inner.embed_query(text)
        return self.queries[text]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return cast("list[list[float]]", self.inner.embed_documents(texts))


class _FallbackChatModel:
    """Chat adapter failing over across configured API keys."""

    def __init__(self, clients: Sequence[Any]) -> None:
        self._pool: _FailoverPool[Any] = _FailoverPool(clients)

    @property
    def active_index(self) -> int:
        return self._pool.active_index

    def model_dump(self, **kwargs: Any) -> Any:
        return self._pool._clients[self.active_index].model_dump(**kwargs)

    def invoke(self, messages: Any, **kwargs: Any) -> Any:
        return self._pool.execute(lambda client: client.invoke(messages, **kwargs))


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
    max_delay: float = 65.0,
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


def error_detail(exc: Exception, *, keys: Sequence[str] = ()) -> str:
    """Report provider causes without exposing any configured API key."""
    from rag.core.config import get_settings

    message = f"{type(exc).__name__}: {exc}"
    if exc.__cause__:
        message += f"; causa: {type(exc.__cause__).__name__}: {exc.__cause__}"
    for key in (*get_settings().google_api_keys, *keys):
        if key:
            message = message.replace(key, "[REDACTED]")
    message = re.sub(r"AIza[\w-]+", "[REDACTED]", message)
    message = re.sub(r"(?i)(key|api_key)=([^&\s]+)", r"\1=[REDACTED]", message)
    return " ".join(message.split())[:1200]


def google_embeddings(
    model: str,
    api_key: str | Sequence[str],
    *,
    fallback_keys: Sequence[str] = (),
) -> Any:
    """Build an embeddings adapter supporting primary plus optional fallback API keys."""
    keys = normalize_api_keys(api_key, fallback_keys)
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    clients = [GoogleGenerativeAIEmbeddings(model=model, api_key=SecretStr(k)) for k in keys]
    return clients[0] if len(clients) == 1 else _FallbackEmbeddings(clients)


def google_chat(
    model: str,
    api_key: str | Sequence[str],
    *,
    fallback_keys: Sequence[str] = (),
) -> Any:
    """Build a chat adapter supporting primary plus optional fallback API keys."""
    keys = normalize_api_keys(api_key, fallback_keys)
    from langchain_google_genai import ChatGoogleGenerativeAI

    normalized_model = model.lower().rsplit("/", 1)[-1]
    sampling: dict[str, Any] = (
        {}
        if normalized_model.startswith(("gemini-3.5-flash-lite", "gemini-3.6-flash"))
        else {"temperature": 0}
    )
    clients = [
        ChatGoogleGenerativeAI(
            model=model,
            api_key=SecretStr(key),
            timeout=60,
            max_retries=0,
            **sampling,
        )
        for key in keys
    ]
    return clients[0] if len(clients) == 1 else _FallbackChatModel(clients)
