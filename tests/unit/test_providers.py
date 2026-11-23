from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import langchain_google_genai
import pytest

from rag import config as config_mod
from rag.providers import (
    CachedQueryEmbeddings,
    error_detail,
    google_chat,
    google_embeddings,
    invoke_with_retry,
    is_key_failover_error,
    normalize_api_keys,
)


def test_cached_query_embeddings_reuses_vector_for_same_question() -> None:
    calls: list[str] = []

    class Inner:
        def embed_query(self, text: str) -> list[float]:
            calls.append(text)
            return [float(len(text))]

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[float(len(text))] for text in texts]

    cached = CachedQueryEmbeddings(Inner())
    assert cached.embed_query("teste") == [5.0]
    assert cached.embed_query("teste") == [5.0]
    assert cached.embed_query("outro") == [5.0]
    assert calls == ["teste", "outro"]
    assert cached.embed_documents(["abc"]) == [[3.0]]


def test_google_chat_omits_temperature_for_fixed_sampling_models(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_chat(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", fake_chat)
    google_chat("gemini-3.5-flash-lite", "not-a-real-key")
    assert "temperature" not in captured


def test_google_chat_keeps_deterministic_temperature_for_supported_models(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_chat(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", fake_chat)
    google_chat("gemini-2.5-flash", "not-a-real-key")
    assert captured["temperature"] == 0
    assert captured["max_retries"] == 0


def test_settings_reads_primary_and_two_fallback_keys_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config_mod,
        "_env",
        lambda: {
            "APP_GOOGLE_API_KEY": " primary-key ",
            "APP_GOOGLE_API_KEY_FALLBACK_1": "fallback-one",
            "APP_GOOGLE_API_KEY_FALLBACK_2": "fallback-one",
        },
    )
    loaded = config_mod.get_settings()
    assert loaded.google_api_keys == ("primary-key", "fallback-one")
    assert loaded.has_google_api_key is True

    monkeypatch.setattr(
        config_mod,
        "_env",
        lambda: {
            "APP_GOOGLE_API_KEY": "",
            "APP_GOOGLE_API_KEY_FALLBACK_1": "backup-1",
            "APP_GOOGLE_API_KEY_FALLBACK_2": "backup-2",
        },
    )
    only_fallbacks = config_mod.get_settings()
    assert only_fallbacks.google_api_keys == ("backup-1", "backup-2")
    assert only_fallbacks.has_google_api_key is True


def test_normalize_api_keys_rejects_blank_inputs() -> None:
    with pytest.raises(ValueError, match="APP_GOOGLE_API_KEY"):
        normalize_api_keys("", ("   ", ""))
    assert normalize_api_keys("k1", ("k2", "k1", "k3")) == ("k1", "k2", "k3")
    assert normalize_api_keys([" k1 ", "k2", "k3"]) == ("k1", "k2", "k3")


def test_google_chat_failover_switches_on_quota_and_auth_and_skips_exhausted_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    mode_by_key = {
        "key-1": "daily_quota",
        "key-2": "invalid_key",
        "key-3": "ok",
    }

    class FakeChatClient:
        def __init__(self, *, api_key: Any, **kwargs: Any) -> None:
            self.raw_key = api_key.get_secret_value()

        def invoke(self, messages: Any, **kwargs: Any) -> Any:
            calls.append(self.raw_key)
            state = mode_by_key[self.raw_key]
            if state == "daily_quota":
                raise RuntimeError("429 per day limit exceeded / daily quota")
            if state == "invalid_key":
                raise RuntimeError("403 API_KEY_INVALID: API key not valid")
            return SimpleNamespace(content=f"ok-{self.raw_key}")

    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", FakeChatClient)
    chat = google_chat("gemini-3.5-flash-lite", ("key-1", "key-2", "key-3"))
    delays: list[float] = []
    first = invoke_with_retry(chat, [("human", "oi")], sleep=delays.append)
    assert first.content == "ok-key-3"
    assert calls == ["key-1", "key-2", "key-3"]
    assert delays == []

    # Exhausted keys remain skipped on subsequent turns.
    calls.clear()
    second = invoke_with_retry(chat, [("human", "oi novamente")], sleep=delays.append)
    assert second.content == "ok-key-3"
    assert calls == ["key-3"]


def test_google_chat_does_not_burn_fallback_keys_on_non_key_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class FakeChatClient:
        def __init__(self, *, api_key: Any, **kwargs: Any) -> None:
            self.raw_key = api_key.get_secret_value()

        def invoke(self, messages: Any, **kwargs: Any) -> Any:
            calls.append(self.raw_key)
            raise RuntimeError("503 Service Unavailable")

    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", FakeChatClient)
    exc = RuntimeError("503 Service Unavailable")
    assert not is_key_failover_error(exc)

    chat = google_chat("gemini-3.5-flash-lite", ("key-1", "key-2", "key-3"))
    with pytest.raises(RuntimeError, match="503"):
        chat.invoke([("human", "oi")])
    assert calls == ["key-1"]


def test_google_chat_transient_rate_limit_rotates_and_preserves_key_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    calls: list[str] = []

    class FakeChatClient:
        def __init__(self, *, api_key: Any, **kwargs: Any) -> None:
            self.raw_key = api_key.get_secret_value()

        def invoke(self, messages: Any, **kwargs: Any) -> Any:
            nonlocal attempts
            attempts += 1
            calls.append(self.raw_key)
            if attempts == 1 and self.raw_key == "key-1":
                raise RuntimeError("429 Too Many Requests; retry in 1s")
            if attempts == 2 and self.raw_key == "key-2":
                return SimpleNamespace(content="from-key-2")
            if attempts == 3 and self.raw_key == "key-2":
                raise RuntimeError("429 Too Many Requests; retry in 1s")
            return SimpleNamespace(content=f"recovered-{self.raw_key}")

    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", FakeChatClient)
    chat = google_chat("gemini-3.5-flash-lite", ("key-1", "key-2"))
    assert chat.invoke([("human", "1")]).content == "from-key-2"
    assert chat.invoke([("human", "2")]).content == "recovered-key-1"
    assert calls == ["key-1", "key-2", "key-2", "key-1"]


def test_google_embeddings_failover_covers_documents_and_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    class FakeEmbeddings:
        def __init__(self, *, model: str, api_key: Any) -> None:
            self.raw_key = api_key.get_secret_value()

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            calls.append(("docs", self.raw_key))
            if self.raw_key == "emb-1":
                raise RuntimeError("429 daily quota exceeded")
            if self.raw_key == "emb-2":
                raise PermissionError("401 Unauthorized")
            return [[0.1, 0.2] for _ in texts]

        def embed_query(self, text: str) -> list[float]:
            calls.append(("query", self.raw_key))
            return [0.3, 0.4]

    monkeypatch.setattr(langchain_google_genai, "GoogleGenerativeAIEmbeddings", FakeEmbeddings)
    emb = google_embeddings("models/gemini-embedding-2", ("emb-1", "emb-2", "emb-3"))
    assert emb.embed_documents(["a", "b"]) == [[0.1, 0.2], [0.1, 0.2]]
    assert emb.embed_query("consulta") == [0.3, 0.4]
    assert calls == [
        ("docs", "emb-1"),
        ("docs", "emb-2"),
        ("docs", "emb-3"),
        ("query", "emb-3"),
    ]


def test_error_detail_redacts_primary_and_fallback_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config_mod,
        "_env",
        lambda: {
            "APP_GOOGLE_API_KEY": "secret-primary-val",
            "APP_GOOGLE_API_KEY_FALLBACK_1": "secret-fb1-val",
            "APP_GOOGLE_API_KEY_FALLBACK_2": "secret-fb2-val",
        },
    )
    msg = error_detail(
        RuntimeError(
            "failed with secret-primary-val and secret-fb1-val and "
            "secret-fb2-val and AIzaFakeSecretToken123"
        )
    )
    assert "secret-primary-val" not in msg
    assert "secret-fb1-val" not in msg
    assert "secret-fb2-val" not in msg
    assert "AIzaFakeSecretToken123" not in msg
    assert "[REDACTED]" in msg


def test_env_example_allows_empty_fallback_keys_and_rejects_filled_fallback() -> None:
    from pathlib import Path

    from rag.config import ROOT
    from scripts.package_delivery import inspect_content

    env_example = ROOT / ".env.example"
    inspect_content(Path(".env.example"), env_example.read_bytes())
    with pytest.raises(ValueError, match="empty API key"):
        inspect_content(
            Path(".env.example"),
            b"APP_GOOGLE_API_KEY=\nAPP_GOOGLE_API_KEY_FALLBACK_1=not-empty\n",
        )
