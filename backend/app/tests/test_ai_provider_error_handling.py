import asyncio

import httpx
import openai
import pytest
from fastapi import HTTPException

from app.services.ai.providers.openai_provider import OpenAIProvider


def _make_request():
    return httpx.Request("POST", "https://api.example.com/v1/messages")


def _make_response(status_code: int, body: bytes):
    return httpx.Response(status_code, content=body, request=_make_request())


def test_openai_connection_error_becomes_http_exception(monkeypatch):
    provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")

    async def _raise(*args, **kwargs):
        raise openai.APIConnectionError(request=_make_request())

    monkeypatch.setattr(provider.client.chat.completions, "create", _raise)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(provider.complete("system", "user"))
    assert exc_info.value.status_code == 503


def test_openai_status_error_forwards_status_without_leaking_body(monkeypatch):
    provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
    secret_marker = b'{"error": {"message": "INTERNAL-TRACE-do-not-leak"}}'

    async def _raise(*args, **kwargs):
        raise openai.APIStatusError(
            "boom", response=_make_response(429, secret_marker), body=None
        )

    monkeypatch.setattr(provider.client.chat.completions, "create", _raise)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(provider.complete("system", "user"))
    assert exc_info.value.status_code == 429
    assert b"INTERNAL-TRACE-do-not-leak" not in str(exc_info.value.detail).encode()
