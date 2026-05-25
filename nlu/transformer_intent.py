"""Optional Transformer-based intent classifier scaffold.
This file provides a thin wrapper around `transformers` but falls back
gracefully when not installed. Use `config.USE_TRANSFORMER_NLU` to enable.
"""
import logging
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    _transformers_available = True
except Exception:
    _transformers_available = False

logger = logging.getLogger(__name__)


class TransformerIntent:
    def __init__(self, model_name_or_path: str = "distilbert-base-uncased"):
        if not _transformers_available:
            raise RuntimeError("transformers not available")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name_or_path)
        self.pipe = pipeline("text-classification", model=self.model, tokenizer=self.tokenizer)

    def predict(self, text: str):
        # Returns (label, score)
        res = self.pipe(text, top_k=1)[0]
        return res.get("label"), res.get("score")
