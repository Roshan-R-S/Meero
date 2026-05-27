import json
import pickle
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import config

with open(config.INTENTS_FILE, encoding="utf-8") as file:
    data = json.load(file)

model = load_model(config.MODEL_FILE)

with open(config.TOKENIZER_FILE, "rb") as f:
    tokenizer = pickle.load(f)

with open(config.LABEL_ENCODER_FILE, "rb") as encoder_file:
    label_encoder = pickle.load(encoder_file)

while True:
    input_text = input("Enter your command-> ")
    padded_sequences = pad_sequences(
        tokenizer.texts_to_sequences([input_text]), maxlen=config.NEURAL_NET_MAXLEN, truncating='post'
    )
    result = model.predict(padded_sequences)
    tag = label_encoder.inverse_transform([np.argmax(result)])

    for i in data['intents']:
        if i['tag'] == tag:
            print(np.random.choice(i['responses']))

