import json
import logging
import pickle
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Embedding, GlobalAveragePooling1D, Dropout
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import LabelEncoder
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open(config.INTENTS_FILE) as file:
    data = json.load(file)

training_sentences = []
training_labels = []
labels = []
responses = []

for intent in data['intents']:
    for pattern in intent['patterns']:
        training_sentences.append(pattern)
        training_labels.append(intent['tag'])
    responses.append(intent['responses'])

    if intent['tag'] not in labels:
        labels.append(intent['tag'])

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

history = model.fit(
    padded_sequences,
    np.array(training_labels),
    epochs=500,          # Max epochs (early stopping will likely trigger sooner)
    validation_split=0.2,  # 20% held out for validation
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

logger.info("Model and artifacts saved successfully.")