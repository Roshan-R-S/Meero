import os
import json
import pickle
import hashlib
import datetime
import random
import argparse

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Embedding, GlobalAveragePooling1D, Dropout
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

import config


def train(vocab_size=1000, embedding_dim=16, maxlen=20, epochs=20, lr=0.001, out_prefix=None):
    SEED = getattr(config, "REPRO_SEED", 42)
    os.environ.setdefault("PYTHONHASHSEED", str(SEED))
    random.seed(SEED)
    np.random.seed(SEED)
    tf.random.set_seed(SEED)

    with open(config.INTENTS_FILE, "rb") as file:
        raw_bytes = file.read()
        data = json.loads(raw_bytes.decode("utf-8"))

    dataset_hash = hashlib.sha256(raw_bytes).hexdigest()

    training_sentences = []
    training_labels = []
    for intent in data['intents']:
        for pattern in intent.get('patterns', []):
            training_sentences.append(pattern)
            training_labels.append(intent['tag'])

    labels = sorted(set(training_labels))
    number_of_classes = len(labels)

    label_encoder = LabelEncoder()
    label_encoder.fit(training_labels)
    y = label_encoder.transform(training_labels)

    tokenizer = Tokenizer(num_words=vocab_size, oov_token="<OOV>")
    tokenizer.fit_on_texts(training_sentences)
    sequences = tokenizer.texts_to_sequences(training_sentences)
    X = pad_sequences(sequences, truncating='post', maxlen=maxlen)

    model = Sequential()
    model.add(Embedding(vocab_size, embedding_dim, input_length=maxlen))
    model.add(GlobalAveragePooling1D())
    model.add(Dense(16, activation="relu"))
    model.add(Dropout(0.3))
    model.add(Dense(16, activation="relu"))
    model.add(Dropout(0.3))
    model.add(Dense(number_of_classes, activation="softmax"))

    opt = tf.keras.optimizers.Adam(learning_rate=lr)
    model.compile(loss='sparse_categorical_crossentropy', optimizer=opt, metrics=["accuracy"])

    early_stop = EarlyStopping(monitor='loss', patience=10, restore_best_weights=True, verbose=0)

    y_array = np.array(y)
    from collections import Counter
    counts = Counter(y_array)
    if min(counts.values()) >= 2:
        X_train, X_val, y_train, y_val = train_test_split(X, y_array, test_size=0.2, random_state=SEED, stratify=y_array)
        history = model.fit(X_train, y_train, epochs=epochs, validation_data=(X_val, y_val), callbacks=[early_stop], verbose=0)
    else:
        history = model.fit(X, y_array, epochs=epochs, callbacks=[early_stop], verbose=0)

    prefix = out_prefix or f"models/sweep_v{vocab_size}_e{embedding_dim}_m{maxlen}_lr{lr}"
    model_path = prefix + ".h5"
    tokenizer_path = prefix + "_tokenizer.pkl"
    label_path = prefix + "_label.pkl"

    model.save(model_path)
    with open(tokenizer_path, "wb") as f:
        pickle.dump(tokenizer, f)
    with open(label_path, "wb") as f:
        pickle.dump(label_encoder, f)

    meta = {
        "dataset_hash": dataset_hash,
        "seed": SEED,
        "training_date": datetime.datetime.utcnow().isoformat() + "Z",
        "num_classes": number_of_classes,
        "num_samples": len(training_sentences),
        "vocab_size": vocab_size,
        "embedding_dim": embedding_dim,
        "maxlen": maxlen,
        "epochs": int(len(history.history.get('loss', []))),
    }
    with open(model_path + ".metadata.json", "w", encoding="utf-8") as mf:
        json.dump(meta, mf, indent=2)

    return model_path, tokenizer_path, label_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vocab", type=int, default=1000)
    parser.add_argument("--embed", type=int, default=16)
    parser.add_argument("--maxlen", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    mp, tp, lp = train(args.vocab, args.embed, args.maxlen, args.epochs, args.lr, args.out)
    print(mp, tp, lp)


if __name__ == '__main__':
    main()
