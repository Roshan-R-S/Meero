import json
import pickle
import random

import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

import config


class NeuralNet:
    def __init__(self):
        try:
            self.model = load_model(config.MODEL_FILE)
        except Exception:
            self.model = None

        try:
            with open(config.TOKENIZER_FILE, "rb") as f:
                self.tokenizer = pickle.load(f)
        except Exception:
            self.tokenizer = None

        try:
            with open(config.LABEL_ENCODER_FILE, "rb") as encoder_file:
                self.label_encoder = pickle.load(encoder_file)
        except Exception:
            self.label_encoder = None

        try:
            with open(config.INTENTS_FILE) as file:
                self.intents_data = json.load(file)
        except Exception:
            self.intents_data = {"intents": []}

    def predict(self, query):
        resp, conf = self.predict_with_confidence(query)
        if resp and conf >= getattr(config, "NEURAL_NET_CONFIDENCE_THRESHOLD", 0.8):
            return resp
        return None

    def predict_with_confidence(self, query):
        if not query or query == "None":
            return None, 0.0

        if not self.model or not self.tokenizer or not self.label_encoder:
            return None, 0.0

        try:
            padded_sequences = pad_sequences(
                self.tokenizer.texts_to_sequences([query]),
                maxlen=config.NEURAL_NET_MAXLEN,
                truncating='post'
            )
        except Exception:
            return None, 0.0

        try:
            result = self.model.predict(padded_sequences, verbose=0)
        except Exception:
            return None, 0.0

        max_prob = float(np.max(result))
        predicted_idx = int(np.argmax(result))

        try:
            tag = self.label_encoder.inverse_transform([predicted_idx])[0]
        except Exception:
            return None, max_prob

        for item in self.intents_data.get('intents', []):
            if item.get('tag') == tag:
                return random.choice(item.get('responses', [None])), max_prob

        return None, max_prob
