#!/usr/bin/env python3
import json
import os
import pickle
import statistics
from collections import Counter, defaultdict

import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import text_to_word_sequence

import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config


def load_dataset(intents_path):
    with open(intents_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    texts, labels = [], []
    for intent in data.get('intents', []):
        tag = intent.get('tag')
        for pattern in intent.get('patterns', []):
            texts.append(pattern)
            labels.append(tag)
    return texts, labels


def diagnose(model_path, tokenizer_path, label_path, intents_path, maxlen=None, top_mispreds=20):
    model = load_model(model_path)
    with open(tokenizer_path, 'rb') as f:
        tokenizer = pickle.load(f)
    with open(label_path, 'rb') as f:
        label_encoder = pickle.load(f)

    texts, labels = load_dataset(intents_path)
    maxlen = maxlen or getattr(config, 'NEURAL_NET_MAXLEN', 20)
    sequences = tokenizer.texts_to_sequences(texts)
    X = pad_sequences(sequences, maxlen=maxlen, truncating='post')

    probs = model.predict(X, verbose=0)
    preds_idx = probs.argmax(axis=1)
    preds = label_encoder.inverse_transform(preds_idx)

    # Class distribution
    class_counts = Counter(labels)

    # Confusion: true -> pred -> count
    confusion = defaultdict(Counter)
    for t, p in zip(labels, preds):
        confusion[t][p] += 1

    # Per-class accuracy
    per_class = {}
    for cls, cnt in class_counts.items():
        correct = confusion[cls].get(cls, 0)
        per_class[cls] = {
            'count': cnt,
            'correct': correct,
            'accuracy': correct / cnt if cnt else None,
        }

    # Token coverage: proportion of unique words present in tokenizer.word_index
    all_words = set()
    for t in texts:
        for w in text_to_word_sequence(t):
            all_words.add(w)
    tk_words = set(tokenizer.word_index.keys())
    covered = sum(1 for w in all_words if w in tk_words)
    token_coverage = covered / len(all_words) if all_words else 1.0

    # Top mispredictions (by prob of predicted class)
    mispreds = []
    for text, true, pred_idx, prob_vec in zip(texts, labels, preds_idx, probs):
        pred_label = label_encoder.inverse_transform([pred_idx])[0]
        if pred_label != true:
            mispreds.append((text, true, pred_label, float(prob_vec[pred_idx]), prob_vec.tolist()))
    mispreds.sort(key=lambda x: x[3], reverse=True)

    report = {
        'model': os.path.basename(model_path),
        'samples': len(texts),
        'class_counts': dict(class_counts),
        'per_class': per_class,
        'token_coverage': token_coverage,
        'unique_tokens': len(all_words),
        'top_mispredictions': [
            {'text': t, 'true': tr, 'pred': pr, 'pred_conf': conf} for t, tr, pr, conf, _ in mispreds[:top_mispreds]
        ],
    }

    return report


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='models/chat_model.h5')
    parser.add_argument('--tokenizer', default='models/tokenizer.pkl')
    parser.add_argument('--label', default='models/label_encoder.pkl')
    parser.add_argument('--intents', default='intents.json')
    parser.add_argument('--out', default='models/diagnostics.json')
    args = parser.parse_args()

    report = diagnose(args.model, args.tokenizer, args.label, args.intents)
    print(json.dumps(report, indent=2))
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print('Wrote diagnostics to', args.out)


if __name__ == '__main__':
    main()
