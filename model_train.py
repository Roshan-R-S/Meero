import os
import json
import logging
import pickle
import hashlib
import datetime
import random
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Embedding, GlobalAveragePooling1D, Dropout
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sklearn.model_selection import train_test_split
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import LabelEncoder
import config

# Deterministic seeds for reproducibility
SEED = getattr(config, "REPRO_SEED", 42)
os.environ.setdefault("PYTHONHASHSEED", str(SEED))
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)
# Enable deterministic ops where supported
os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open(config.INTENTS_FILE, "rb") as file:
    raw_bytes = file.read()
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception:
        # fallback if file already in text mode
        data = json.loads(raw_bytes)

# Compute a dataset hash for versioning
dataset_hash = hashlib.sha256(raw_bytes).hexdigest()

training_sentences = []
training_labels = []
responses = []

for intent in data['intents']:
    patterns = intent.get('patterns', [])
    for pattern in patterns:
        training_sentences.append(pattern)
        training_labels.append(intent['tag'])
    responses.append(intent.get('responses', []))

# Derive labels from actual training labels to avoid empty-intent mismatch
labels = sorted(set(training_labels))
number_of_classes = len(labels)
logger.info("Number of classes: %d", number_of_classes)
logger.info("Number of training samples: %d", len(training_sentences))

label_encoder = LabelEncoder()
label_encoder.fit(training_labels)
training_labels = label_encoder.transform(training_labels)

tokenizer = Tokenizer(num_words=config.NEURAL_NET_VOCAB_SIZE, oov_token="<OOV>")
tokenizer.fit_on_texts(training_sentences)
sequences = tokenizer.texts_to_sequences(training_sentences)
padded_sequences = pad_sequences(sequences, truncating='post', maxlen=config.NEURAL_NET_MAXLEN)

model = Sequential()
model.add(Embedding(config.NEURAL_NET_VOCAB_SIZE, config.NEURAL_NET_EMBEDDING_DIM, input_length=config.NEURAL_NET_MAXLEN))
model.add(GlobalAveragePooling1D())
model.add(Dense(16, activation="relu"))
model.add(Dropout(0.3))  # Regularization to reduce overfitting
model.add(Dense(16, activation="relu"))
model.add(Dropout(0.3))
model.add(Dense(number_of_classes, activation="softmax"))

model.compile(loss='sparse_categorical_crossentropy', optimizer="adam", metrics=["accuracy"])

model.summary()

# Early stopping: stop training when loss stops improving
early_stop = EarlyStopping(
    monitor='loss',
    patience=50,        # Wait 50 epochs after loss stops improving
    restore_best_weights=True,
    verbose=1
)

y_array = np.array(training_labels)
# If every class has at least 2 samples, use stratified split; otherwise train on full set
from collections import Counter
class_counts = Counter(y_array)
if min(class_counts.values()) >= 2:
    X_train, X_val, y_train, y_val = train_test_split(padded_sequences, y_array, test_size=0.2, random_state=SEED, stratify=y_array)
    history = model.fit(
        X_train,
        y_train,
        epochs=500,
        validation_data=(X_val, y_val),
        callbacks=[early_stop],
        verbose=1
    )
else:
    history = model.fit(
        padded_sequences,
        y_array,
        epochs=500,
        callbacks=[early_stop],
        verbose=1
    )

logger.info("Training complete. Final loss: %.4f", history.history['loss'][-1])
if 'val_loss' in history.history:
    logger.info("Final val_loss: %.4f", history.history['val_loss'][-1])

model.save(config.MODEL_FILE)

with open(config.TOKENIZER_FILE, "wb") as f:
    pickle.dump(tokenizer, f, protocol=pickle.HIGHEST_PROTOCOL)

with open(config.LABEL_ENCODER_FILE, "wb") as encoder_file:
    pickle.dump(label_encoder, encoder_file, protocol=pickle.HIGHEST_PROTOCOL)

# Save metadata including dataset hash and environment info
metadata = {
    "dataset_hash": dataset_hash,
    "seed": SEED,
    "training_date": datetime.datetime.utcnow().isoformat() + "Z",
    "num_classes": number_of_classes,
    "num_samples": len(training_sentences),
    "numpy_version": np.__version__,
    "tensorflow_version": tf.__version__,
}

meta_path = f"{config.MODEL_FILE}.metadata.json"
with open(meta_path, "w", encoding="utf-8") as mf:
    json.dump(metadata, mf, indent=2)

logger.info("Model, artifacts, and metadata saved successfully. Dataset hash: %s", dataset_hash)