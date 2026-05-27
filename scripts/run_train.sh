#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

if [ "$1" = "--install" ]; then
  echo "Installing pinned requirements..."
  pip install -r requirements.txt
fi

export PYTHONHASHSEED=42
export TF_DETERMINISTIC_OPS=1
export TF_ENABLE_ONEDNN_OPTS=0
export OMP_NUM_THREADS=1

echo "Starting deterministic training..."
python model_train.py 2>&1 | tee training.log
echo "Training complete. Logs: training.log"
