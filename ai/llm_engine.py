import logging
import os

try:
    from gpt4all import GPT4All
except ImportError:
    GPT4All = None

from core.prompt_templates import build_local_prompt, clean_llm_response

logger = logging.getLogger(__name__)


class LLMEngine:
    def __init__(self, model_path):
        logger.info("Loading LLM from: %s...", model_path)

        if GPT4All is None:
            raise RuntimeError("gpt4all is not installed; local LLM fallback is unavailable")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at: {model_path}")

        model_dir = os.path.dirname(os.path.abspath(model_path))
        model_filename = os.path.basename(model_path)
        self.model_filename = model_filename

        self.llm = GPT4All(model_name=model_filename, model_path=model_dir, allow_download=False)
        logger.info("LLM Loaded successfully.")

    def generate_response(self, user_input, history=None, memory_summary=None):
        if history is None:
            history = []
        try:
            prompt = build_local_prompt(
                self.model_filename,
                user_input,
                history,
                memory_summary=memory_summary,
            )
            response = self.llm.generate(prompt, max_tokens=100, temp=0.7)
            return clean_llm_response(response)

        except Exception:
            logger.exception("GPT4All generation error")
            return "I am having trouble accessing my higher brain functions."
