import json
import logging
import pickle
import random

import numpy as np
from tensorflow.keras.preprocessing.sequence import pad_sequences

import config
from ai.keras_compat import load_model_compat

logger = logging.getLogger(__name__)


class NeuralNet:
    def __init__(self):
        self.model = self._load_model(config.MODEL_FILE)
        self.tokenizer = self._load_pickle(config.TOKENIZER_FILE, "tokenizer")
        self.label_encoder = self._load_pickle(config.LABEL_ENCODER_FILE, "label encoder")
        self.intents_data = self._load_intents(config.INTENTS_FILE)

    @staticmethod
    def _load_model(model_path):
        try:
            return load_model_compat(model_path)
        except Exception:
            logger.exception("Failed to load neural model from %s", model_path)
            return None

    @staticmethod
    def _load_pickle(path, label):
        try:
            with open(path, "rb") as file_handle:
                return pickle.load(file_handle)
        except Exception:
            logger.exception("Failed to load %s from %s", label, path)
            return None

    @staticmethod
    def _load_intents(path):
        try:
            with open(path) as file_handle:
                return json.load(file_handle)
        except Exception:
            logger.exception("Failed to load intents from %s", path)
            return {"intents": []}

    def predict(self, query):
        resp, conf, tag = self.predict_with_confidence(query)
        if resp and conf >= getattr(config, "NEURAL_NET_CONFIDENCE_THRESHOLD", 0.8):
            return resp
        return None

    def predict_with_confidence(self, query):
        if not query or query == "None":
            return None, 0.0, None

        if not self.model or not self.tokenizer or not self.label_encoder:
            return None, 0.0, None

        try:
            padded_sequences = pad_sequences(
                self.tokenizer.texts_to_sequences([query]),
                maxlen=config.NEURAL_NET_MAXLEN,
                truncating='post'
            )
        except Exception:
            return None, 0.0, None

        try:
            result = self.model.predict(padded_sequences, verbose=0)
        except Exception:
            return None, 0.0, None

        max_prob = float(np.max(result))
        predicted_idx = int(np.argmax(result))

        try:
            tag = self.label_encoder.inverse_transform([predicted_idx])[0]
        except Exception:
            return None, max_prob, None

        for item in self.intents_data.get('intents', []):
            if item.get('tag') == tag:
                return random.choice(item.get('responses', [None])), max_prob, tag

        return None, max_prob, tag
