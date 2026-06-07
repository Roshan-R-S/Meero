# Reproducible Training

Use `scripts/train_and_package.py` as the canonical training path. It trains the
intent classifier from `data/intents.json`, writes versioned artifacts, refreshes the
canonical runtime artifacts, and updates `models/manifest.json`.

## Direct Run

```powershell
python scripts/train_and_package.py --epochs 100 --batch 8 --out-dir models
```

To train with the three bundled local GGUF teacher models, run:

```powershell
python scripts/train_and_package.py --epochs 100 --batch 8 --use-default-teachers --teacher-examples-per-model 2 --out-dir models
```

The teacher stage writes `models/intents.teacher_augmented.json` and records the teacher manifest in `models/manifest.json`.

## Deterministic Runners

PowerShell:

```powershell
.\scripts\run_train.ps1 -InstallRequirements
```

Bash / WSL:

```bash
./scripts/run_train.sh --install
```

The runners set deterministic environment variables before invoking the
canonical training script:

- `PYTHONHASHSEED=42`
- `TF_DETERMINISTIC_OPS=1`
- `TF_ENABLE_ONEDNN_OPTS=0`
- `OMP_NUM_THREADS=1`

The runtime app loads only these canonical files:

- `models/chat_model.h5`
- `models/tokenizer.pkl`
- `models/label_encoder.pkl`

## Evaluation Gate

Evaluate the current canonical artifacts with:

```powershell
python scripts/evaluate.py --out models/local_eval.json
```

The evaluator fails when accuracy is below `0.85` by default. Override the
threshold explicitly for experiments:

```powershell
python scripts/evaluate.py --out models/local_eval.json --min-accuracy 0.80
```

CI uses the same gate for the main-branch evaluation workflow. The workflow
defaults to `MODEL_EPOCHS=100`; the current small classifier does not reliably
clear the `0.85` gate with very short smoke-training runs such as 5 epochs.
