"""Adaptadores LangChain para Gemini; chave e modelos vêm do .env."""

from __future__ import annotations

import re
from typing import Any

from pydantic import SecretStr


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
