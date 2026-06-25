"""
train_reader.py — Module 1 training script (run once, offline).

Trains the two Keras LSTM classifiers (issue + frustration) on
backend/data/messages.csv and saves the four artifacts the Reader needs:

    backend/models/reader_issue.keras
    backend/models/reader_frustration.keras
    backend/models/tokenizer.json
    backend/models/label_maps.json

Usage (from anywhere):
    python backend/modules/reader/train_reader.py

Extracted from Module1_The_Reader.ipynb (owner: Reader sub-team). The notebook
additionally runs the SimpleRNN-vs-LSTM comparison and the plots; this script
keeps only what is needed to produce the shipped artifacts. Seed = 42.
"""

import json
import os

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import LSTM, Dense, Dropout, Embedding
from tensorflow.keras.models import Sequential
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer

SEED = 42
VOCAB = 3000
MAXLEN = 40

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, "..", "..", "data", "messages.csv")
_MODEL_DIR = os.path.join(_HERE, "..", "..", "models")


def _build_model(n_classes: int) -> Sequential:
    model = Sequential([
        Embedding(VOCAB, 64, input_length=MAXLEN),
        LSTM(64),
        Dropout(0.3),
        Dense(32, activation="relu"),
        Dense(n_classes, activation="softmax"),
    ])
    model.compile(loss="sparse_categorical_crossentropy",
                  optimizer="adam", metrics=["accuracy"])
    return model


def main() -> None:
    np.random.seed(SEED)
    tf.random.set_seed(SEED)

    messages = pd.read_csv(_DATA)
    print(f"Loaded {len(messages)} messages from {_DATA}")

    tok = Tokenizer(num_words=VOCAB, oov_token="<OOV>")
    tok.fit_on_texts(messages.text)
    X = pad_sequences(tok.texts_to_sequences(messages.text), maxlen=MAXLEN)

    issue_labels = sorted(messages.issue_type.unique())
    frust_labels = sorted(messages.frustration.unique())
    issue_to_id = {lab: i for i, lab in enumerate(issue_labels)}
    frust_to_id = {lab: i for i, lab in enumerate(frust_labels)}
    y_issue = messages.issue_type.map(issue_to_id).values
    y_frust = messages.frustration.map(frust_to_id).values

    Xtr, Xte, yi_tr, yi_te, yf_tr, yf_te = train_test_split(
        X, y_issue, y_frust, test_size=0.2, random_state=SEED, stratify=y_issue
    )

    early = EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True)

    print("Training issue model (LSTM)...")
    issue_model = _build_model(len(issue_labels))
    issue_model.fit(Xtr, yi_tr, validation_data=(Xte, yi_te),
                    epochs=20, batch_size=16, callbacks=[early], verbose=2)

    print("Training frustration model (LSTM)...")
    frust_model = _build_model(len(frust_labels))
    frust_model.fit(Xtr, yf_tr, validation_data=(Xte, yf_te),
                    epochs=20, batch_size=16, callbacks=[early], verbose=2)

    os.makedirs(_MODEL_DIR, exist_ok=True)
    issue_model.save(os.path.join(_MODEL_DIR, "reader_issue.keras"))
    frust_model.save(os.path.join(_MODEL_DIR, "reader_frustration.keras"))

    with open(os.path.join(_MODEL_DIR, "tokenizer.json"), "w", encoding="utf-8") as f:
        f.write(tok.to_json())

    label_maps = {
        "issue_to_id": issue_to_id,
        "id_to_issue": {str(i): lab for lab, i in issue_to_id.items()},
        "frust_to_id": frust_to_id,
        "id_to_frust": {str(i): lab for lab, i in frust_to_id.items()},
        "VOCAB": VOCAB,
        "MAXLEN": MAXLEN,
    }
    with open(os.path.join(_MODEL_DIR, "label_maps.json"), "w", encoding="utf-8") as f:
        json.dump(label_maps, f, indent=2)

    te_issue = issue_model.evaluate(Xte, yi_te, verbose=0)[1]
    te_frust = frust_model.evaluate(Xte, yf_te, verbose=0)[1]
    print(f"Done. Test accuracy — issue {te_issue:.3f} | frustration {te_frust:.3f}")
    print(f"Artifacts written to {os.path.abspath(_MODEL_DIR)}")


if __name__ == "__main__":
    main()
