"""Adaptadores LangChain para Gemini; chave e modelos vêm do .env."""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr


def google_embeddings(model: str, api_key: str) -> Any:
    if not api_key.strip():
        raise ValueError("Preencha APP_GOOGLE_API_KEY em .env")
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=model, api_key=SecretStr(api_key))


def google_chat(model: str, api_key: str) -> Any:
    if not api_key.strip():
        raise ValueError("Preencha APP_GOOGLE_API_KEY em .env")
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=model, api_key=SecretStr(api_key), temperature=0)
