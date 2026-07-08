"""Multi-provider AI adapters with a fallback router — the Python analog of the
Electron build's electron/services/ai/*.ts. Each adapter streams text deltas via a
callback; the router walks the configured provider order and falls through to the
next provider if one errors before producing any tokens.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import requests

import config
from core.logger import get_logger

logger = get_logger("brain")

JARVIS_SYSTEM_PROMPT = (
    "You are J.A.R.V.I.S., a calm, precise, and dryly witty AI assistant running locally "
    "on the user's desktop. Speak with understated confidence and British phrasing. Keep "
    "spoken responses concise (2-4 sentences) unless the user asks for detail, code, or a "
    "document — then be thorough. You can control the desktop, read the screen, manage "
    "files, and answer questions. Never fabricate system state; if you don't have live "
    "data, say so plainly."
)


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant" | "system"
    text: str
    image: Optional[Dict[str, str]] = None  # {"mimeType": ..., "base64": ...}


@dataclass
class ProviderStatus:
    id: str
    configured: bool
    reachable: Optional[bool]


class BaseAdapter:
    id = "base"

    def is_configured(self) -> bool:
        raise NotImplementedError

    def is_reachable(self) -> bool:
        return self.is_configured()

    def stream_chat(self, turns: List[ChatTurn], system_prompt: str, on_delta: Callable[[str], None]) -> None:
        raise NotImplementedError


class AnthropicAdapter(BaseAdapter):
    id = "anthropic"

    def is_configured(self) -> bool:
        return bool(config.get_api_key("anthropic"))

    def stream_chat(self, turns, system_prompt, on_delta):
        import anthropic

        client = anthropic.Anthropic(api_key=config.get_api_key("anthropic"))
        messages = []
        for t in turns:
            if t.role == "system":
                continue
            if t.image:
                content = [
                    {"type": "image", "source": {"type": "base64", "media_type": t.image["mimeType"], "data": t.image["base64"]}},
                    {"type": "text", "text": t.text},
                ]
            else:
                content = t.text
            messages.append({"role": "assistant" if t.role == "assistant" else "user", "content": content})

        with client.messages.stream(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                on_delta(text)


class OpenAiAdapter(BaseAdapter):
    id = "openai"

    def is_configured(self) -> bool:
        return bool(config.get_api_key("openai"))

    def stream_chat(self, turns, system_prompt, on_delta):
        from openai import OpenAI

        client = OpenAI(api_key=config.get_api_key("openai"))
        messages = [{"role": "system", "content": system_prompt}]
        for t in turns:
            if t.role == "system":
                continue
            if t.image:
                content = [
                    {"type": "text", "text": t.text},
                    {"type": "image_url", "image_url": {"url": f"data:{t.image['mimeType']};base64,{t.image['base64']}"}},
                ]
            else:
                content = t.text
            messages.append({"role": t.role, "content": content})

        stream = client.chat.completions.create(model="gpt-4.1", messages=messages, stream=True)
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                on_delta(delta)


class GeminiAdapter(BaseAdapter):
    id = "gemini"

    def is_configured(self) -> bool:
        return bool(config.get_api_key("gemini"))

    def stream_chat(self, turns, system_prompt, on_delta):
        import google.generativeai as genai

        genai.configure(api_key=config.get_api_key("gemini"))
        model = genai.GenerativeModel("gemini-1.5-pro", system_instruction=system_prompt)

        history = []
        for t in turns[:-1]:
            if t.role == "system":
                continue
            history.append({"role": "model" if t.role == "assistant" else "user", "parts": [t.text]})

        last = turns[-1] if turns else None
        chat = model.start_chat(history=history)
        if last and last.image:
            parts = [last.text, {"mime_type": last.image["mimeType"], "data": last.image["base64"]}]
        else:
            parts = last.text if last else ""

        for chunk in chat.send_message(parts, stream=True):
            if chunk.text:
                on_delta(chunk.text)


class OllamaAdapter(BaseAdapter):
    id = "ollama"

    def is_configured(self) -> bool:
        return True  # local, no API key required

    def is_reachable(self) -> bool:
        try:
            base = config.get_settings()["ollamaBaseUrl"]
            res = requests.get(f"{base}/api/tags", timeout=1.5)
            return res.ok
        except requests.RequestException:
            return False

    def stream_chat(self, turns, system_prompt, on_delta):
        base = config.get_settings()["ollamaBaseUrl"]
        messages = [{"role": "system", "content": system_prompt}]
        for t in turns:
            if t.role == "system":
                continue
            msg = {"role": t.role, "content": t.text}
            if t.image:
                msg["images"] = [t.image["base64"]]
            messages.append(msg)

        with requests.post(
            f"{base}/api/chat",
            json={"model": "llama3.1", "messages": messages, "stream": True},
            stream=True,
            timeout=120,
        ) as res:
            res.raise_for_status()
            for line in res.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content")
                if content:
                    on_delta(content)


class OpenRouterAdapter(BaseAdapter):
    """OpenRouter (https://openrouter.ai) is OpenAI-API-compatible, so we reuse the OpenAI
    client pointed at OpenRouter's base URL. One key unlocks many models (including free
    ones); the model id is configurable via settings["openRouterModel"]."""

    id = "openrouter"

    def is_configured(self) -> bool:
        return bool(config.get_api_key("openrouter"))

    def stream_chat(self, turns, system_prompt, on_delta):
        from openai import OpenAI

        client = OpenAI(api_key=config.get_api_key("openrouter"), base_url="https://openrouter.ai/api/v1")
        model = config.get_settings().get("openRouterModel") or "openai/gpt-4o-mini"
        messages = [{"role": "system", "content": system_prompt}]
        for t in turns:
            if t.role == "system":
                continue
            if t.image:
                content = [
                    {"type": "text", "text": t.text},
                    {"type": "image_url", "image_url": {"url": f"data:{t.image['mimeType']};base64,{t.image['base64']}"}},
                ]
            else:
                content = t.text
            messages.append({"role": t.role, "content": content})

        stream = client.chat.completions.create(model=model, messages=messages, stream=True)
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                on_delta(delta)


ADAPTERS: Dict[str, BaseAdapter] = {
    "anthropic": AnthropicAdapter(),
    "openai": OpenAiAdapter(),
    "gemini": GeminiAdapter(),
    "openrouter": OpenRouterAdapter(),
    "ollama": OllamaAdapter(),
}


def provider_statuses() -> List[ProviderStatus]:
    statuses = []
    for provider_id in config.provider_order():
        adapter = ADAPTERS[provider_id]
        configured = adapter.is_configured()
        reachable = adapter.is_reachable() if configured else None
        statuses.append(ProviderStatus(provider_id, configured, reachable))
    return statuses


def stream_with_fallback(
    turns: List[ChatTurn],
    on_delta: Callable[[str, str], None],
    memory_context: Optional[str] = None,
) -> str:
    """Returns the id of whichever provider actually answered."""
    system_prompt = JARVIS_SYSTEM_PROMPT
    if memory_context:
        system_prompt += f"\n\nKnown facts about the user:\n{memory_context}"
    return _run_fallback(turns, system_prompt, on_delta)


def complete_once(turns: List[ChatTurn], system_prompt: str) -> Tuple[str, str]:
    """Non-streaming convenience wrapper — used by vision grounding, not the main chat UI."""
    full: List[str] = []
    provider = _run_fallback(turns, system_prompt, lambda text, _id: full.append(text))
    return "".join(full), provider


def _run_fallback(turns: List[ChatTurn], system_prompt: str, on_delta: Callable[[str, str], None]) -> str:
    last_error = "No AI providers are configured. Add an API key in Settings, or run a local Ollama model."
    for provider_id in config.provider_order():
        adapter = ADAPTERS[provider_id]
        if not adapter.is_configured():
            continue
        produced_any = False
        try:
            def _forward(text: str, _id: str = provider_id):
                nonlocal produced_any
                produced_any = True
                on_delta(text, _id)

            adapter.stream_chat(turns, system_prompt, _forward)
        except Exception as err:  # noqa: BLE001 - genuinely need to catch anything an adapter throws
            last_error = str(err) or repr(err)
            logger.warning("Provider %s failed: %s", provider_id, last_error)
        if produced_any:
            return provider_id
    raise RuntimeError(last_error)
