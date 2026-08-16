"""Prompt builders for Meero's LLM fallback path with tool calling support."""
from __future__ import annotations

import json
import re
from typing import Any, Iterable

SYSTEM_PROMPT = """You are Meero, a local AI assistant for Roshan.

Rules:
- Be concise and useful.
- Do not claim you performed desktop actions unless the action engine did it.
- If the user asks for dangerous system actions, ask for confirmation.
- Use memory summary only as context, not as guaranteed truth.
- If unsure, say so clearly."""

TOOL_INSTRUCTIONS = """You have access to desktop tools to execute user requests.
If the user wants you to perform actions, output ONLY a JSON object:
{"tool_calls": [{"tool": "tool_name", "args": {"param": "value"}}]}
Multiple actions can be chained in the "tool_calls" list.
If no action is needed, output normal conversational text without JSON."""

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
    include_tools: bool = True,
) -> str:
    """Build a stable Llama-3 style prompt for local GGUF/GPT4All models."""
    from .tool_registry import format_tools_for_prompt

    turns = list(history or [])[-max_history:]
    system_text = SYSTEM_PROMPT
    if include_tools:
        system_text += f"\n\n{TOOL_INSTRUCTIONS}\n\n{format_tools_for_prompt()}"
    if memory_summary:
        system_text += f"\n\nMemory summary:\n{memory_summary}"

    prompt = "<|begin_of_text|>"
    prompt += _format_turn("system", system_text)
    for query, response in turns:
        prompt += _format_turn("user", query)
        prompt += _format_turn("assistant", response)
    prompt += _format_turn("user", user_input)
    prompt += "<|start_header_id|>assistant<|end_header_id|>\n"
    return prompt


def build_mistral_prompt(
    user_input: str,
    history: Iterable[tuple[str, str]] | None = None,
    memory_summary: str | None = None,
    max_history: int = 5,
    include_tools: bool = True,
) -> str:
    """Build a Mistral Instruct style prompt for local GGUF/GPT4All models."""
    from .tool_registry import format_tools_for_prompt

    turns = list(history or [])[-max_history:]
    system_text = SYSTEM_PROMPT
    if include_tools:
        system_text += f"\n\n{TOOL_INSTRUCTIONS}\n\n{format_tools_for_prompt()}"
    if memory_summary:
        system_text += f"\n\nMemory summary:\n{memory_summary}"

    prompt = "<s>"
    if not turns:
        return f"{prompt}[INST] {system_text}\n\n{user_input.strip()} [/INST]"

    first_query, first_response = turns[0]
    prompt += f"[INST] {system_text}\n\n{first_query.strip()} [/INST] {first_response.strip()}</s>"
    for query, response in turns[1:]:
        prompt += f"[INST] {query.strip()} [/INST] {response.strip()}</s>"
    prompt += f"[INST] {user_input.strip()} [/INST]"
    return prompt


def build_local_prompt(
    model_name: str | None,
    user_input: str,
    history: Iterable[tuple[str, str]] | None = None,
    memory_summary: str | None = None,
    include_tools: bool = True,
) -> str:
    """Choose a prompt format based on the local GGUF model filename."""
    normalized_name = (model_name or "").lower()
    if "mistral" in normalized_name or "mixtral" in normalized_name:
        return build_mistral_prompt(user_input, history, memory_summary=memory_summary, include_tools=include_tools)
    return build_llama3_prompt(user_input, history, memory_summary=memory_summary, include_tools=include_tools)


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


def extract_tool_calls(text: str | None) -> list[dict[str, Any]] | None:
    """
    Robustly extract and validate JSON tool calls from LLM output.
    Returns a list of dicts: [{"tool": str, "args": dict}] or None if text is conversational.
    """
    if not text:
        return None

    cleaned = text.strip()
    
    # 1. Check for markdown code blocks ```json ... ``` or ``` ... ```
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    candidate_json = code_block_match.group(1) if code_block_match else None

    # 2. If no code block, look for bare JSON object containing tool_calls
    if not candidate_json:
        json_obj_match = re.search(r"(\{.*\"tool_calls\"\s*:\s*\[.*\]\s*\})", cleaned, re.DOTALL)
        if json_obj_match:
            candidate_json = json_obj_match.group(1)

    if not candidate_json and cleaned.startswith("{") and cleaned.endswith("}"):
        candidate_json = cleaned

    if candidate_json:
        try:
            data = json.loads(candidate_json)
            if isinstance(data, dict) and "tool_calls" in data and isinstance(data["tool_calls"], list):
                valid_calls = []
                for item in data["tool_calls"]:
                    if isinstance(item, dict) and "tool" in item:
                        valid_calls.append({
                            "tool": str(item["tool"]),
                            "args": item.get("args", {}) if isinstance(item.get("args"), dict) else {},
                        })
                if valid_calls:
                    return valid_calls
        except Exception:
            pass

    return None
