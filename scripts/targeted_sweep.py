import json
import time
import os
import random
import hashlib
import datetime

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Embedding, GlobalAveragePooling1D, Dropout
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split

import config


def train_large(vocab_size=2000, embedding_dim=64, maxlen=30, dense_units=64, epochs=20, lr=0.001, out_prefix=None):
    SEED = getattr(config, "REPRO_SEED", 42)
    os.environ.setdefault("PYTHONHASHSEED", str(SEED))
    random.seed(SEED)
    np.random.seed(SEED)
    tf.random.set_seed(SEED)

    with open(config.INTENTS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

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
    model.add(Dense(dense_units, activation="relu"))
    model.add(Dropout(0.3))
    model.add(Dense(dense_units, activation="relu"))
    model.add(Dropout(0.3))
    model.add(Dense(number_of_classes, activation="softmax"))

    opt = tf.keras.optimizers.Adam(learning_rate=lr)
    model.compile(loss='sparse_categorical_crossentropy', optimizer=opt, metrics=["accuracy"])

    early_stop = EarlyStopping(monitor='loss', patience=8, restore_best_weights=True, verbose=0)

    y_array = np.array(y)
    from collections import Counter
    counts = Counter(y_array)
    if min(counts.values()) >= 2:
        X_train, X_val, y_train, y_val = train_test_split(X, y_array, test_size=0.2, random_state=SEED, stratify=y_array)
        history = model.fit(X_train, y_train, epochs=epochs, validation_data=(X_val, y_val), callbacks=[early_stop], verbose=0)
    else:
        history = model.fit(X, y_array, epochs=epochs, callbacks=[early_stop], verbose=0)

    prefix = out_prefix or f"models/large_v{vocab_size}_e{embedding_dim}_m{maxlen}_d{dense_units}_lr{lr}"
    model_path = prefix + ".h5"
    tokenizer_path = prefix + "_tokenizer.pkl"
    label_path = prefix + "_label.pkl"

    model.save(model_path)
    import pickle
    with open(tokenizer_path, "wb") as f:
        pickle.dump(tokenizer, f)
    with open(label_path, "wb") as f:
        pickle.dump(label_encoder, f)

    meta = {
        "seed": SEED,
        "training_date": datetime.datetime.utcnow().isoformat() + "Z",
        "num_classes": number_of_classes,
        "num_samples": len(training_sentences),
        "vocab_size": vocab_size,
        "embedding_dim": embedding_dim,
        "maxlen": maxlen,
        "dense_units": dense_units,
        "epochs": int(len(history.history.get('loss', []))),
    }
    with open(model_path + ".metadata.json", "w", encoding="utf-8") as mf:
        json.dump(meta, mf, indent=2)

    return model_path, tokenizer_path, label_path


def main():
    # quick validation run
    mp, tp, lp = train_large(vocab_size=2000, embedding_dim=64, maxlen=30, dense_units=64, epochs=20, lr=0.001)
    print(mp, tp, lp)


if __name__ == '__main__':
    main()
