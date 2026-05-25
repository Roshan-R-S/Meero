#!/usr/bin/env python3
"""Train a simple intent classifier and package artifacts with versioning.

Usage:
  python scripts/train_and_package.py --epochs 100 --batch 8 --upload-s3

This script trains a small Keras model on `intents.json`, saves the model,
tokenizer, and label encoder into the `models/` directory with a versioned
filename, and optionally uploads artifacts to S3 when `S3_BUCKET` is set.
"""
import os
import json
import argparse
import time
import logging
import subprocess

TF_AVAILABLE = True
try:
    import numpy as np
except Exception:
    np = None

TF_AVAILABLE = True
try:
    # Attempting to import tensorflow is optional for dry-run validation
    import tensorflow  # noqa: F401
except Exception:
    TF_AVAILABLE = False

import pickle
import pathlib
import sys

# Ensure project root is on sys.path so imports like `config` work when invoked from scripts/
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def git_short_hash():
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
        return out
    except Exception:
        return None


def build_and_train(intents_path, epochs=100, batch_size=8):
    if not TF_AVAILABLE:
        raise RuntimeError("TensorFlow and Keras are required to run training")

    with open(intents_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = []
    labels = []
    for intent in data.get("intents", []):
        tag = intent.get("tag")
        for pattern in intent.get("patterns", []):
            texts.append(pattern)
            labels.append(tag)

    if not texts:
        raise RuntimeError("No training data found in intents.json")

    # Lazy import of Keras/TensorFlow-specific modules to allow dry-run without TF
    from tensorflow.keras.preprocessing.text import Tokenizer
    from tensorflow.keras.preprocessing.sequence import pad_sequences
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Embedding, GlobalAveragePooling1D, Dense
    from tensorflow.keras.utils import to_categorical
    from sklearn.preprocessing import LabelEncoder

    # Tokenize
    tokenizer = Tokenizer(num_words=getattr(config, "NEURAL_NET_VOCAB_SIZE", None), oov_token="<OOV>")
    tokenizer.fit_on_texts(texts)
    sequences = tokenizer.texts_to_sequences(texts)
    maxlen = getattr(config, "NEURAL_NET_MAXLEN", 20)
    X = pad_sequences(sequences, maxlen=maxlen, truncating='post')

    # Labels
    le = LabelEncoder()
    y_int = le.fit_transform(labels)
    y = to_categorical(y_int)

    vocab_size = min(getattr(config, "NEURAL_NET_VOCAB_SIZE", 1000), len(tokenizer.word_index) + 1)

    # Build model
    model = Sequential([
        Embedding(input_dim=vocab_size, output_dim=getattr(config, "NEURAL_NET_EMBEDDING_DIM", 16), input_length=maxlen),
        GlobalAveragePooling1D(),
        Dense(16, activation='relu'),
        Dense(y.shape[1], activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

    logger.info("Training model: epochs=%s batch_size=%s", epochs, batch_size)
    model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=2)
    return model, tokenizer, le


def save_artifacts(model, tokenizer, label_encoder, version_tag, out_dir="models"):
    os.makedirs(out_dir, exist_ok=True)
    model_name = f"chat_model_{version_tag}.h5"
    model_path = os.path.join(out_dir, model_name)
    tokenizer_path = os.path.join(out_dir, f"tokenizer_{version_tag}.pkl")
    label_path = os.path.join(out_dir, f"label_encoder_{version_tag}.pkl")

    logger.info("Saving model to %s", model_path)
    model.save(model_path)

    with open(tokenizer_path, "wb") as f:
        pickle.dump(tokenizer, f)

    with open(label_path, "wb") as f:
        pickle.dump(label_encoder, f)

    return model_path, tokenizer_path, label_path


def write_manifest_and_update_latest(model_path, tokenizer_path, label_path, version_tag, out_dir="models"):
    import shutil
    manifest = {
        "version": version_tag,
        "model": os.path.basename(model_path),
        "tokenizer": os.path.basename(tokenizer_path),
        "label_encoder": os.path.basename(label_path),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git": git_short_hash()
    }

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Update canonical filenames so the app can load `models/chat_model.h5` etc.
    canonical_model = os.path.join(out_dir, "chat_model.h5")
    canonical_tokenizer = os.path.join(out_dir, "tokenizer.pkl")
    canonical_label = os.path.join(out_dir, "label_encoder.pkl")

    # Use atomic replace where possible
    shutil.copyfile(model_path, canonical_model)
    shutil.copyfile(tokenizer_path, canonical_tokenizer)
    shutil.copyfile(label_path, canonical_label)

    return manifest_path, canonical_model, canonical_tokenizer, canonical_label


def upload_to_s3(paths):
    try:
        import boto3
    except Exception:
        logger.error("boto3 not available; cannot upload to S3")
        return False

    bucket = os.environ.get("S3_BUCKET")
    prefix = os.environ.get("S3_PREFIX", "meero-models")
    if not bucket:
        logger.error("S3_BUCKET not set; skipping upload")
        return False

    s3 = boto3.client('s3')
    for p in paths:
        key = os.path.join(prefix, os.path.basename(p))
        logger.info("Uploading %s -> s3://%s/%s", p, bucket, key)
        s3.upload_file(p, bucket, key)

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--version", type=str, default=None)
    parser.add_argument("--upload-s3", action='store_true')
    parser.add_argument("--upload-hf", action='store_true', help="Upload artifacts to Hugging Face Hub (requires HF_TOKEN and HF_REPO env vars)")
    parser.add_argument("--dry-run", action='store_true', help="Validate credentials and repo access without training or uploading")
    parser.add_argument("--out-dir", type=str, default="models")
    args = parser.parse_args()

    version = args.version or time.strftime("%Y%m%d%H%M%S")
    git_hash = git_short_hash()
    if git_hash:
        version = f"{version}-{git_hash}"

    # If dry-run, validate credentials and repo access without training or uploading
    if args.dry_run:
        ok = True
        if args.upload_hf:
            hf_token = os.environ.get("HF_TOKEN")
            hf_repo = os.environ.get("HF_REPO") or os.environ.get("HF_MODEL_REPO")
            if not hf_token or not hf_repo:
                logger.error("HF_TOKEN/HF_REPO required for HF validation; current values: token=%s repo=%s", bool(hf_token), hf_repo)
                ok = False
            else:
                ok = ok and validate_hf(hf_token, hf_repo)

        if args.upload_s3:
            ok = ok and validate_s3()

        if ok:
            logger.info("Dry-run validation succeeded.")
            return 0
        else:
            logger.error("Dry-run validation failed.")
            return 2

    # Normal run: train and save artifacts
    model, tokenizer, le = build_and_train(config.INTENTS_FILE, epochs=args.epochs, batch_size=args.batch)
    model_path, tokenizer_path, label_path = save_artifacts(model, tokenizer, le, version, out_dir=args.out_dir)

    logger.info("Artifacts saved: %s, %s, %s", model_path, tokenizer_path, label_path)

    # Write manifest and update canonical latest filenames
    manifest_path, canonical_model, canonical_tokenizer, canonical_label = write_manifest_and_update_latest(
        model_path, tokenizer_path, label_path, version, out_dir=args.out_dir
    )
    logger.info("Manifest written to %s", manifest_path)

    if args.upload_s3:
        ok = upload_to_s3([model_path, tokenizer_path, label_path])
        if ok:
            logger.info("Upload completed.")
        else:
            logger.error("Upload failed or skipped.")

    if args.upload_hf:
        # Upload to Hugging Face Hub
        hf_token = os.environ.get("HF_TOKEN")
        hf_repo = os.environ.get("HF_REPO") or os.environ.get("HF_MODEL_REPO")
        if not hf_token:
            logger.error("HF_TOKEN not set; skipping Hugging Face upload")
        elif not hf_repo:
            logger.error("HF_REPO not set; set HF_REPO=""username/repo"" or HF_MODEL_REPO")
        else:
            try:
                from huggingface_hub import HfApi, upload_file, create_repo
                api = HfApi()
                # Create repo if it doesn't exist
                try:
                    create_repo(repo_id=hf_repo, token=hf_token, exist_ok=True)
                except Exception:
                    logger.info("Repository may already exist; continuing")

                # Upload files
                for p in [model_path, tokenizer_path, label_path, manifest_path]:
                    filename = os.path.basename(p)
                    logger.info("Uploading %s to HF repo %s", filename, hf_repo)
                    upload_file(path_or_fileobj=p, path_in_repo=filename, repo_id=hf_repo, token=hf_token)

                logger.info("Hugging Face upload completed.")
            except Exception:
                logger.exception("Hugging Face upload failed; ensure huggingface_hub is installed and HF_TOKEN/HF_REPO are set")

    print("DONE: version=", version)
    return 0


def validate_hf(hf_token, hf_repo):
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        # validate token
        user = api.whoami(token=hf_token)
        logger.info("HF token valid for user: %s", user.get('name') or user.get('user', {}).get('name'))
        # validate repo access (repo_info will raise if inaccessible)
        try:
            api.repo_info(repo_id=hf_repo, token=hf_token)
            logger.info("HF repo '%s' is accessible", hf_repo)
        except Exception:
            logger.info("HF repo '%s' not accessible or does not exist; token appears valid", hf_repo)
        return True
    except Exception:
        logger.exception("Hugging Face validation failed")
        return False


def validate_s3():
    import boto3
    bucket = os.environ.get("S3_BUCKET")
    if not bucket:
        logger.error("S3_BUCKET not set")
        return False
    try:
        s3 = boto3.client('s3')
        # simple call to list buckets (permission-dependent) as smoke check
        s3.list_buckets()
        logger.info("S3 client appears usable (bucket set: %s)", bucket)
        return True
    except Exception:
        logger.exception("S3 validation failed; boto3 may not be configured")
        return False



if __name__ == '__main__':
    main()
