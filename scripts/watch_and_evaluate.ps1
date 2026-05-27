Param(
    [int]$PollSeconds = 10
)

Write-Host "Watcher started; polling for model metadata every $PollSeconds seconds..."

$meta = Join-Path -Path (Join-Path -Path (Get-Location) -ChildPath "models") -ChildPath "chat_model.h5.metadata.json"
while (-not (Test-Path $meta)) {
    Start-Sleep -Seconds $PollSeconds
}

Write-Host "Metadata found: $meta -- running evaluation"
$venv_py = Join-Path -Path (Get-Location) -ChildPath ".venv\Scripts\python.exe"
if (Test-Path $venv_py) {
    & $venv_py -m scripts.evaluate --model models/chat_model.h5 --tokenizer models/tokenizer.pkl --label-encoder models/label_encoder.pkl --intents intents.json --out models/last_eval.json
} else {
    Write-Host "Virtualenv python not found; falling back to system python"
    python -m scripts.evaluate --model models/chat_model.h5 --tokenizer models/tokenizer.pkl --label-encoder models/label_encoder.pkl --intents intents.json --out models/last_eval.json
}
Write-Host "Evaluation complete; results at models/last_eval.json"
