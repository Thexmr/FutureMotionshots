"""Unified async LLM client across Anthropic / OpenAI-compatible / Ollama.

Providers expose different wire formats; this normalises them behind two calls:
`complete()` (text + optional tool-calling) and `vision()` (image understanding).
Tool schemas are provider-neutral and translated per provider so the agent code
never branches on provider.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from ..models.settings import ProviderConfig

ANTHROPIC_VERSION = "2023-06-01"
_RETRYABLE = {408, 409, 429, 500, 502, 503, 504}


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class LLMResult:
    text: str
    tool_calls: list[ToolCall]
    raw: dict[str, Any]


class AIClient:
    """One client per provider config. Stateless apart from the http session."""

    def __init__(self, provider: ProviderConfig):
        self.provider = provider
        self.id = provider.id

    # -- public API -------------------------------------------------------- #
    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.4,
    ) -> LLMResult:
        if self.id == "anthropic":
            return await self._anthropic(model, messages, tools, max_tokens, temperature)
        return await self._openai_compatible(model, messages, tools, max_tokens, temperature)

    async def vision(self, model: str, prompt: str, image_bytes: bytes) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        if self.id == "anthropic":
            content = [
                {"type": "text", "text": prompt},
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/jpeg", "data": b64}},
            ]
            res = await self._anthropic(model, [{"role": "user", "content": content}], None, 1024, 0.2)
            return res.text
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]
        res = await self._openai_compatible(
            model, [{"role": "user", "content": content}], None, 1024, 0.2)
        return res.text

    # -- providers --------------------------------------------------------- #
    def _base_url(self) -> str:
        if self.provider.base_url:
            return self.provider.base_url.rstrip("/")
        return {
            "anthropic": "https://api.anthropic.com",
            "openai": "https://api.openai.com/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "ollama": "http://localhost:11434",
        }.get(self.id, "")

    async def _anthropic(self, model, messages, tools, max_tokens, temperature) -> LLMResult:
        system = ""
        conv = []
        for m in messages:
            if m["role"] == "system":
                system += (m["content"] if isinstance(m["content"], str) else "") + "\n"
            else:
                conv.append(m)
        payload: dict[str, Any] = {
            "model": model, "max_tokens": max_tokens, "temperature": temperature,
            "messages": conv,
        }
        if system.strip():
            payload["system"] = system.strip()
        if tools:
            payload["tools"] = [
                {"name": t["name"], "description": t["description"],
                 "input_schema": t["parameters"]} for t in tools
            ]
        data = await self._post(
            f"{self._base_url()}/v1/messages", payload,
            headers={
                "x-api-key": self.provider.api_key or "",
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
        )
        text, calls = "", []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block["text"]
            elif block.get("type") == "tool_use":
                calls.append(ToolCall(block["id"], block["name"], block.get("input", {})))
        return LLMResult(text=text, tool_calls=calls, raw=data)

    async def _openai_compatible(self, model, messages, tools, max_tokens, temperature) -> LLMResult:
        is_ollama = self.id == "ollama"
        url = (f"{self._base_url()}/api/chat" if is_ollama
               else f"{self._base_url()}/chat/completions")
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if is_ollama:
            payload["stream"] = False
            payload["options"] = {"temperature": temperature}
        else:
            payload["max_tokens"] = max_tokens
            payload["temperature"] = temperature
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]

        headers = {"content-type": "application/json"}
        if self.provider.api_key and not is_ollama:
            headers["Authorization"] = f"Bearer {self.provider.api_key}"
        data = await self._post(url, payload, headers=headers)

        if is_ollama:
            msg = data.get("message", {})
            text = msg.get("content", "")
            calls = [
                ToolCall(f"call_{i}", tc["function"]["name"],
                         tc["function"].get("arguments", {}))
                for i, tc in enumerate(msg.get("tool_calls", []) or [])
            ]
            return LLMResult(text=text, tool_calls=calls, raw=data)

        choice = (data.get("choices") or [{}])[0].get("message", {})
        calls = []
        for tc in choice.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(tc.get("id", ""), fn.get("name", ""), args))
        return LLMResult(text=choice.get("content") or "", tool_calls=calls, raw=data)

    async def _post(self, url: str, payload: dict, headers: dict, attempts: int = 3) -> dict:
        delay = 1.0
        last_exc: Optional[Exception] = None
        async with httpx.AsyncClient(timeout=120) as client:
            for attempt in range(attempts):
                try:
                    r = await client.post(url, json=payload, headers=headers)
                    if r.status_code in (401, 403):
                        raise PermissionError(f"{self.id} auth failed: {r.text[:200]}")
                    if r.status_code in _RETRYABLE and attempt < attempts - 1:
                        await _sleep(delay)
                        delay *= 2
                        continue
                    r.raise_for_status()
                    return r.json()
                except (httpx.TransportError, httpx.TimeoutException) as exc:
                    last_exc = exc
                    if attempt < attempts - 1:
                        await _sleep(delay)
                        delay *= 2
                        continue
                    raise
        if last_exc:
            raise last_exc
        raise RuntimeError("request failed")


async def _sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)
