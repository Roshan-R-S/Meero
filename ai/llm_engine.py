import logging
import os
import threading
from typing import Any, Optional

try:
    from gpt4all import GPT4All
except ImportError:
    GPT4All = None

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

import config
from core.prompt_templates import build_local_prompt, clean_llm_response, extract_tool_calls

logger = logging.getLogger(__name__)


class LLMEngine:
    def __init__(self, model_path: str):
        logger.info("Loading LLM from: %s...", model_path)

        if GPT4All is None and Llama is None:
            raise RuntimeError("Neither gpt4all nor llama_cpp is installed; local LLM fallback is unavailable")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at: {model_path}")

        model_dir = os.path.dirname(os.path.abspath(model_path))
        model_filename = os.path.basename(model_path)
        self.model_filename = model_filename
        self._lock = threading.Lock()
        device = getattr(config, "LLM_DEVICE", "cpu")
        self._backend = "gpt4all"
        self.llm: Any = None

        is_llama_cpp_first = "qwen" in model_filename.lower() or "phi" in model_filename.lower()
        loaded = False

        if not is_llama_cpp_first and GPT4All is not None:
            try:
                self.llm = GPT4All(
                    model_name=model_filename,
                    model_path=model_dir,
                    allow_download=False,
                    device=device,
                )
                self._backend = "gpt4all"
                loaded = True
                logger.info("LLM Loaded successfully via GPT4All on device: %s.", device)
            except Exception as gpt_exc:
                logger.info("GPT4All could not load %s (%s); trying llama_cpp...", model_filename, gpt_exc)

        if not loaded:
            if Llama is None:
                raise RuntimeError("Neither GPT4All nor llama_cpp could load the model")
            n_gpu = -1 if device == "gpu" else 0
            self.llm = Llama(
                model_path=str(model_path),
                n_gpu_layers=n_gpu,
                n_ctx=2048,
                verbose=False,
            )
            self._backend = "llama_cpp"
            logger.info("LLM Loaded successfully via llama_cpp (GPU layers: %s).", n_gpu)

    def generate_response(self, user_input: str, history=None, memory_summary=None, max_tokens: int = 150) -> str:
        """Generate a standard text response."""
        if history is None:
            history = []
        try:
            prompt = build_local_prompt(
                self.model_filename,
                user_input,
                history,
                memory_summary=memory_summary,
                include_tools=True,
            )
            with self._lock:
                if self._backend == "llama_cpp":
                    resp = self.llm(prompt=prompt, max_tokens=max_tokens, temperature=0.7)
                    choices = resp.get("choices", []) if isinstance(resp, dict) else []
                    response = choices[0].get("text", "") if choices else str(resp)
                else:
                    response = self.llm.generate(prompt, max_tokens=max_tokens, temp=0.7)
            return clean_llm_response(response)
        except Exception:
            logger.exception("LLM generation error (%s)", self._backend)
            return "I am having trouble accessing my higher brain functions."

    def generate_with_tools(
        self, user_input: str, history=None, memory_summary=None
    ) -> tuple[Optional[list[dict[str, Any]]], str]:
        """
        Generate response with structured tool call parsing.
        Returns (tool_calls, raw_text).
        If tool calls were detected, tool_calls is a list of dicts, otherwise None.
        """
        raw_output = self.generate_response(user_input, history=history, memory_summary=memory_summary)
        tool_calls = extract_tool_calls(raw_output)
        return tool_calls, raw_output

    def generate_response_stream(
        self, user_input: str, history=None, memory_summary=None, max_tokens: int | None = None
    ):
        """Generate response tokens as a stream."""
        if history is None:
            history = []
        tokens_limit = max_tokens or getattr(config, "VOICE_LLM_MAX_TOKENS", 96)
        try:
            prompt = build_local_prompt(
                self.model_filename,
                user_input,
                history,
                memory_summary=memory_summary,
                include_tools=True,
            )
            with self._lock:
                if self._backend == "llama_cpp":
                    for chunk in self.llm(prompt=prompt, max_tokens=tokens_limit, temperature=0.7, stream=True):
                        choices = chunk.get("choices", []) if isinstance(chunk, dict) else []
                        token = choices[0].get("text", "") if choices else ""
                        if token:
                            yield token
                else:
                    for token in self.llm.generate(prompt, max_tokens=tokens_limit, temp=0.7, streaming=True):
                        yield token
        except Exception:
            logger.exception("LLM streaming generation error (%s)", self._backend)
            yield "I am having trouble accessing my higher brain functions."

