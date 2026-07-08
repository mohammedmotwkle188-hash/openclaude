"""The AI brain: Groq first (free, fast, official), with OpenRouter and Gemini as optional
fallbacks. All three are reached through the OpenAI-compatible client except Gemini, which
uses its own SDK only if that key is set. You normally only need a Groq key.

Streaming: each adapter calls on_delta(text) for each chunk. The router walks the provider
order and reports EVERY provider's real error if they all fail (so you see the true reason,
not a misleading last-in-chain message).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import config

logger_prefix = "[brain]"


def _log(msg: str) -> None:
    print(f"{logger_prefix} {msg}", flush=True)


JARVIS_SYSTEM_PROMPT = (
    "You are J.A.R.V.I.S., a calm, precise, dryly witty AI assistant running on the user's "
    "desktop. Speak with understated confidence and British phrasing. Keep spoken replies "
    "concise (2-4 sentences) unless asked for detail, code, or a document. Never fabricate "
    "live system state; if you don't have real data, say so plainly."
)


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant" | "system"
    text: str


@dataclass
class ProviderStatus:
    id: str
    configured: bool
    reachable: Optional[bool]


class BaseAdapter:
    id = "base"

    def is_configured(self) -> bool:
        raise NotImplementedError

    def stream_chat(self, turns: List[ChatTurn], system_prompt: str, on_delta: Callable[[str], None]) -> None:
        raise NotImplementedError


class _OpenAICompatibleAdapter(BaseAdapter):
    """Shared implementation for any OpenAI-API-compatible endpoint (Groq, OpenRouter)."""

    base_url = ""
    key_field = ""
    model_setting = ""
    default_model = ""

    def is_configured(self) -> bool:
        return bool(config.get_api_key(self.key_field))

    def _model(self) -> str:
        return config.get_settings().get(self.model_setting) or self.default_model

    def stream_chat(self, turns, system_prompt, on_delta):
        from openai import OpenAI

        client = OpenAI(api_key=config.get_api_key(self.key_field), base_url=self.base_url)
        messages = [{"role": "system", "content": system_prompt}]
        for t in turns:
            if t.role == "system":
                continue
            messages.append({"role": t.role, "content": t.text})
        stream = client.chat.completions.create(model=self._model(), messages=messages, stream=True)
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                on_delta(delta)


class GroqAdapter(_OpenAICompatibleAdapter):
    id = "groq"
    base_url = "https://api.groq.com/openai/v1"
    key_field = "groq"
    model_setting = "groqModel"
    default_model = "llama-3.3-70b-versatile"


class OpenRouterAdapter(_OpenAICompatibleAdapter):
    id = "openrouter"
    base_url = "https://openrouter.ai/api/v1"
    key_field = "openrouter"
    model_setting = "openRouterModel"
    default_model = "meta-llama/llama-3.3-70b-instruct:free"


class GeminiAdapter(BaseAdapter):
    id = "gemini"

    def is_configured(self) -> bool:
        return bool(config.get_api_key("gemini"))

    def stream_chat(self, turns, system_prompt, on_delta):
        import google.generativeai as genai  # imported lazily; optional dependency

        genai.configure(api_key=config.get_api_key("gemini"))
        model_name = config.get_settings().get("geminiModel") or "gemini-2.0-flash"
        model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
        history = [
            {"role": "model" if t.role == "assistant" else "user", "parts": [t.text]}
            for t in turns[:-1]
            if t.role != "system"
        ]
        last = turns[-1] if turns else None
        chat = model.start_chat(history=history)
        for chunk in chat.send_message(last.text if last else "", stream=True):
            if chunk.text:
                on_delta(chunk.text)


ADAPTERS: Dict[str, BaseAdapter] = {
    "groq": GroqAdapter(),
    "openrouter": OpenRouterAdapter(),
    "gemini": GeminiAdapter(),
}


def provider_statuses() -> List[ProviderStatus]:
    out = []
    for pid in config.provider_order():
        adapter = ADAPTERS.get(pid)
        if not adapter:
            continue
        configured = adapter.is_configured()
        out.append(ProviderStatus(pid, configured, configured or None))
    return out


def stream_with_fallback(
    turns: List[ChatTurn],
    on_delta: Callable[[str, str], None],
    memory_context: Optional[str] = None,
) -> str:
    system_prompt = JARVIS_SYSTEM_PROMPT
    if memory_context:
        system_prompt += f"\n\nKnown facts about the user:\n{memory_context}"

    errors: List[str] = []
    any_configured = False
    for pid in config.provider_order():
        adapter = ADAPTERS.get(pid)
        if not adapter or not adapter.is_configured():
            continue
        any_configured = True
        produced = False

        def _forward(text: str, _pid: str = pid):
            nonlocal produced
            produced = True
            on_delta(text, _pid)

        try:
            adapter.stream_chat(turns, system_prompt, _forward)
        except Exception as err:  # noqa: BLE001
            msg = str(err) or repr(err)
            errors.append(f"{pid} → {msg[:180]}")
            _log(f"Provider {pid} failed: {msg}")
        if produced:
            return pid

    if not any_configured:
        raise RuntimeError(
            "No AI key set. Get a free Groq key at console.groq.com/keys, then run: python3 set_key.py"
        )
    raise RuntimeError("Every AI provider failed:\n- " + "\n- ".join(errors))
