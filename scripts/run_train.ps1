Param(
    [switch]$InstallRequirements
)

# Activate virtualenv (assumes .venv in project root)
if (Test-Path -Path .\.venv\Scripts\Activate.ps1) {
    . .\.venv\Scripts\Activate.ps1
}

if ($InstallRequirements) {
    Write-Host "Installing pinned requirements..."
    pip install -r requirements.txt
}

# Reproducible environment variables
$env:PYTHONHASHSEED = "42"
$env:TF_DETERMINISTIC_OPS = "1"
$env:TF_ENABLE_ONEDNN_OPTS = "0"
$env:OMP_NUM_THREADS = "1"

Write-Host "Starting deterministic training..."
python model_train.py 2>&1 | Tee-Object -FilePath training.log

Write-Host "Training complete. Logs: training.log"
