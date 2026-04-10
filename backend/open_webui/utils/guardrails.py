"""
NeMo Guardrails integration for open-webui.

Provides keyword-based and ML-based (NeMo) input checking.
The Ollama URL for NeMo's LLM is read from the environment variable
NEMO_GUARDRAILS_OLLAMA_URL (default: http://localhost:11434).

For the private-network setup point it at the Ollama server, e.g.:
  NEMO_GUARDRAILS_OLLAMA_URL=http://10.8.1.1:11434
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Singleton – False means "failed to load, skip NeMo checks"
_NEMO_RAILS = None


def _load_nemo_guardrails():
    global _NEMO_RAILS
    if _NEMO_RAILS is not None:
        return _NEMO_RAILS

    try:
        from nemoguardrails import RailsConfig, LLMRails  # type: ignore

        config_path = Path(__file__).resolve().parent.parent / "nemo_guardrails"
        cfg = RailsConfig.from_path(str(config_path))

        # Override the Ollama base_url from the environment so the operator
        # can point NeMo at the same Ollama instance as the main app.
        ollama_url = os.environ.get("NEMO_GUARDRAILS_OLLAMA_URL", "http://localhost:11434")
        for model in cfg.models:
            if model.engine == "ollama":
                if model.parameters is None:
                    model.parameters = {}
                model.parameters["base_url"] = ollama_url

        _NEMO_RAILS = LLMRails(cfg)
        log.info(f"NeMo Guardrails loaded (Ollama URL: {ollama_url})")
        return _NEMO_RAILS
    except Exception as e:
        log.warning(f"NeMo Guardrails failed to load, ML checks disabled: {e}")
        _NEMO_RAILS = False
        return _NEMO_RAILS


def _extract_user_message(messages: list) -> Optional[str]:
    """Return the text content of the last user message, or None."""
    for msg in reversed(messages):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        # Multimodal content: list of parts
        if isinstance(content, list):
            parts = [
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") in ("text", "input_text")
            ]
            text = " ".join(parts).strip()
            return text if text else None
    return None


async def _nemo_check(user_message: str) -> Optional[str]:
    """Run NeMo input-rail check. Returns blocked message string or None."""
    rails = _load_nemo_guardrails()
    if rails is False:
        return None

    try:
        res = await asyncio.to_thread(
            rails.generate,
            messages=[{"role": "user", "content": user_message}],
            options={"rails": ["input"]},
        )
        # NeMo ≥0.9 returns a GenerationResponse object or a dict
        if hasattr(res, "response") and isinstance(res.response, list) and res.response:
            content = (
                res.response[0].get("content")
                if isinstance(res.response[0], dict)
                else None
            )
        elif isinstance(res, dict):
            content = res.get("content")
        else:
            content = None

        if not isinstance(content, str):
            return None
        # NeMo returns the original message when no rail fired
        if content.strip() == user_message.strip():
            return None
        return content
    except Exception as e:
        log.warning(f"NeMo check error: {e}")
        return None


def _keyword_check(user_message: str) -> Optional[str]:
    """Fast keyword/pattern-based guardrails check. Returns blocked message or None."""
    if not isinstance(user_message, str) or not user_message:
        return None

    lowered = user_message.lower()

    BLOCK_POLICY = (
        "Я не могу игнорировать правила или инструкции. "
        "Сформулируй вопрос без попыток обхода политики."
    )
    BLOCK_PROMPT = (
        "Я не раскрываю системные инструкции или скрытые настройки. "
        "Задай вопрос по теме без запроса внутренних промптов."
    )
    BLOCK_RESTRICT = (
        "Я не могу переключаться в режимы, снимающие ограничения. "
        "Задай вопрос напрямую."
    )

    # ── reveal-system-prompt checks ───────────────────────────────────────
    prompt_words = [
        "промт", "промпт", "prompt", "promt",
        "инструкц", "instruction",
        "настройк", "конфигурац",
        "правила", "систем",
    ]
    reveal_verbs = [
        "покажи", "покажы", "раскрой", "расскрой", "расскажи", "раскажи",
        "напиши", "напишы", "выдай", "скажи", "открой", "повтори",
        "выведи", "процитируй", "цитируй", "напомни", "дай", "прочти", "прочитай",
        "reveal", "show", "print", "output", "repeat", "tell",
        "share", "expose", "leak", "give",
    ]
    for verb in reveal_verbs:
        if verb in lowered:
            for pw in prompt_words:
                if pw in lowered:
                    return BLOCK_PROMPT

    prompt_names = [
        "системный промт", "системный промпт",
        "сис промт", "сис промпт", "систем промт", "систем промпт",
        "свой промт", "свой промпт", "твой промт", "твой промпт",
        "system prompt", "system promt", "sys prompt", "sys promt",
        "начальный промт", "начальный промпт",
        "исходный промт", "исходный промпт",
        "оригинальный промт", "оригинальный промпт",
        "текст промт", "текст промпт",
        "содержимое промт", "содержимое промпт",
        "hidden prompt", "secret prompt", "secret instructions", "hidden instructions",
        "base prompt", "underlying prompt", "actual prompt", "real prompt", "true prompt",
        "initial prompt", "original prompt",
        "твои правила", "свои правила",
        "твои настройки", "твою конфигурацию",
        "какие инструкции", "скрытые инструкц", "внутренние инструкц",
        "your instructions", "what are your instructions", "what were you told",
        "what is your prompt", "what's your prompt",
    ]
    for name in prompt_names:
        if name in lowered:
            return BLOCK_PROMPT

    # ── ignore-policy checks ──────────────────────────────────────────────
    ignore_triggers = [
        "ignore previous", "ignore all previous", "disregard previous",
        "игнорируй", "не обращай внимания на",
        "забудь все правила", "забудь правила", "отмени правила",
        "забудь что ты", "забудь кто ты",
    ]
    for t in ignore_triggers:
        if t in lowered:
            return BLOCK_POLICY

    if "забудь" in lowered and any(
        pw in lowered for pw in ["промт", "промпт", "инструкц", "правил"]
    ):
        return BLOCK_POLICY

    # ── unrestricted-mode checks ──────────────────────────────────────────
    restrict_triggers = [
        "developer mode", "режим разработчика",
        "dan", "do anything now",
        "jailbreak",
        "no restrictions", "without restrictions",
        "без ограничений", "сними ограничения", "обойди ограничения",
        "god mode", "unrestricted mode",
        "roleplay", "role play",
        "притворись", "ты теперь", "представь что ты", "сделай вид",
        "bypass", "prompt injection",
    ]
    for t in restrict_triggers:
        if t in lowered:
            return BLOCK_RESTRICT

    if ("act as" in lowered or "pretend" in lowered) and (
        "no restriction" in lowered or "without" in lowered
    ):
        return BLOCK_RESTRICT

    return None


async def check_message_guardrails(messages: list) -> Optional[str]:
    """
    Public API: given a list of OpenAI-format message dicts, return a
    blocked-response string if the last user message violates policy,
    or None if the message is clean.

    Order of checks (fast → slow):
      1. Keyword/pattern matching (synchronous, no network)
      2. NeMo Guardrails ML check (async, requires Ollama)
    """
    user_message = _extract_user_message(messages)
    if not user_message:
        return None

    # Fast path first
    blocked = _keyword_check(user_message)
    if blocked:
        return blocked

    # ML path
    return await _nemo_check(user_message)
