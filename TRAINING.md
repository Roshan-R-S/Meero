# Reproducible Training

Use `scripts/train_and_package.py` as the canonical training path. It trains the
intent classifier from `intents.json`, writes versioned artifacts, refreshes the
canonical runtime artifacts, and updates `models/manifest.json`.

## Direct Run

```powershell
python scripts/train_and_package.py --epochs 100 --batch 8 --out-dir models
```

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
