Reproducible training
--------------------

Use the provided scripts to run deterministic training of the neural network.

PowerShell (Windows):

```
.\scripts\run_train.ps1 -InstallRequirements
```

Bash (Unix / WSL):

```
./scripts/run_train.sh --install
```

The runner sets `PYTHONHASHSEED=42`, `TF_DETERMINISTIC_OPS=1`, and `TF_ENABLE_ONEDNN_OPTS=0` to reduce nondeterminism. The training script writes a metadata JSON next to the saved model containing the dataset hash and seed.

If you have a GPU, ensure the virtualenv has the appropriate `tensorflow` build installed.
