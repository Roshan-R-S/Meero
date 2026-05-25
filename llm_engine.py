import logging
import os
from gpt4all import GPT4All
from prompt_templates import build_llama3_prompt, clean_llm_response

logger = logging.getLogger(__name__)

class LLMEngine:
    def __init__(self, model_path):
        """
        Initialize the GPT4All model.
        Args:
            model_path (str): Absolute or relative path to the .gguf model file.
        """
        logger.info("Loading LLM from: %s...", model_path)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at: {model_path}")
            
        model_dir = os.path.dirname(os.path.abspath(model_path))
        model_filename = os.path.basename(model_path)

        # GPT4All expects the model name and path separately usually, but allows path
        self.llm = GPT4All(model_name=model_filename, model_path=model_dir, allow_download=False)
        logger.info("LLM Loaded successfully.")

    def generate_response(self, user_input, history=None, memory_summary=None):
        """
        Generate a response using GPT4All with conversation context.
        Args:
            user_input (str): The user's current query.
            history (list): List of (query, response) tuples.
        """
        if history is None:
            history = []
        try:
            prompt = build_llama3_prompt(user_input, history, memory_summary=memory_summary)
            response = self.llm.generate(prompt, max_tokens=100, temp=0.7)
            return clean_llm_response(response)
            
        except Exception:
            logger.exception("GPT4All generation error")
            return "I am having trouble accessing my higher brain functions."
