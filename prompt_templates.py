"""Prompt builders for Meero's LLM fallback path."""
from __future__ import annotations

import re

from typing import Iterable

SYSTEM_PROMPT = (
    "You are Meero, Roshan's private AI assistant. "
    "Be concise, useful, and action-oriented. "
    "Prefer one or two sentences unless the user asks for detail."
)

ASSISTANT_HEADER = "<|start_header_id|>assistant<|end_header_id|>"
BEGIN_TEXT = "<|begin_of_text|>"
EOT_TOKEN = "<|eot_id|>"
RESERVED_TOKEN_RE = re.compile(r"<\|reserved_special_token_\d+\|>")


def _format_turn(role: str, text: str) -> str:
    return f"<|start_header_id|>{role}<|end_header_id|>\n\n{text}<|eot_id|>"


def build_llama3_prompt(
    user_input: str,
    history: Iterable[tuple[str, str]] | None = None,
    memory_summary: str | None = None,
    max_history: int = 5,
) -> str:
    """Build a stable Llama-3 style prompt for local GGUF/GPT4All models."""
    turns = list(history or [])[-max_history:]
    system_text = SYSTEM_PROMPT
    if memory_summary:
        system_text += f"\nLong-term conversation summary: {memory_summary}"

    prompt = "<|begin_of_text|>"
    prompt += _format_turn("system", system_text)
    for query, response in turns:
        prompt += _format_turn("user", query)
        prompt += _format_turn("assistant", response)
    prompt += _format_turn("user", user_input)
    prompt += "<|start_header_id|>assistant<|end_header_id|>\n"
    return prompt


def build_external_payload(
    user_input: str,
    history: Iterable[tuple[str, str]] | None = None,
    memory_summary: str | None = None,
) -> dict:
    """Create a provider-neutral payload for optional API LLMs."""
    return {
        "system": SYSTEM_PROMPT,
        "input": user_input,
        "history": list(history or []),
        "memory_summary": memory_summary or "",
    }


def clean_llm_response(text: str | None) -> str:
    """Remove prompt artifacts from model output before returning it."""
    if not text:
        return ""

    cleaned = text.strip()
    cleaned = cleaned.replace(BEGIN_TEXT, "")
    cleaned = cleaned.replace(EOT_TOKEN, "")
    cleaned = RESERVED_TOKEN_RE.sub("", cleaned)

    if ASSISTANT_HEADER in cleaned:
        cleaned = cleaned.split(ASSISTANT_HEADER)[-1].strip()

    if "Meero:" in cleaned:
        cleaned = cleaned.rsplit("Meero:", 1)[-1].strip()

    if "Assistant:" in cleaned:
        cleaned = cleaned.rsplit("Assistant:", 1)[-1].strip()

    if cleaned.startswith(SYSTEM_PROMPT):
        cleaned = cleaned[len(SYSTEM_PROMPT):].strip()

    if SYSTEM_PROMPT in cleaned:
        cleaned = cleaned.split(SYSTEM_PROMPT, 1)[-1].strip()

    if cleaned.startswith("User:"):
        cleaned = cleaned.split("User:")[-1].strip()

    return " ".join(cleaned.split())
