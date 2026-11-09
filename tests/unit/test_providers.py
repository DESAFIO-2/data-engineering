from __future__ import annotations

from typing import Any

import langchain_google_genai

from rag.providers import google_chat


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
