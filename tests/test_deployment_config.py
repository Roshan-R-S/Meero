from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _expanded_requirements(name: str, seen=None) -> set[str]:
    seen = set() if seen is None else seen
    if name in seen:
        return set()
    seen.add(name)
    packages = set()
    for raw_line in (ROOT / name).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            packages.update(_expanded_requirements(line[3:].strip(), seen))
        else:
            packages.add(line.split("==", 1)[0].lower())
    return packages


def test_example_environment_is_web_safe_by_default():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "\nLOCAL_DESKTOP_MODE=false\n" in f"\n{example}"
    assert "\nWEB_SAFE_MODE=true\n" in f"\n{example}"


def test_websafe_and_voice_profiles_exclude_desktop_automation():
    websafe = _expanded_requirements("requirements-websafe.txt")
    voice = websafe | _expanded_requirements("requirements-voice.txt")
    desktop = _expanded_requirements("requirements.txt")

    assert "pyautogui" not in websafe
    assert "pyautogui" not in voice
    assert "pyautogui" in desktop


def test_dockerfiles_install_their_named_capability_profiles():
    default = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    websafe = (ROOT / "Dockerfile.websafe").read_text(encoding="utf-8")
    voice = (ROOT / "Dockerfile.voice").read_text(encoding="utf-8")

    assert "-r requirements.txt" in default
    assert "requirements-actions.txt" in default
    assert "requirements-desktop.txt" in default
    assert "-r requirements-websafe.txt" in websafe
    assert "requirements-actions.txt" in websafe
    assert "-r requirements-voice.txt" in voice
    assert "requirements-actions.txt" in voice
    assert "requirements-desktop.txt" not in websafe
    assert "requirements-desktop.txt" not in voice


def test_production_compose_mounts_data_and_models_without_voice_duplicates():
    development = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    production = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    voice = (ROOT / "docker-compose.voice.yml").read_text(encoding="utf-8")

    assert "LOCAL_DESKTOP_MODE=${LOCAL_DESKTOP_MODE:-false}" in development
    assert "WEB_SAFE_MODE=${WEB_SAFE_MODE:-true}" in development
    assert "./data:/app/data" in production
    assert "./models:/app/models:ro" in production
    assert "RATE_LIMIT_FAIL_OPEN=false" in production
    assert "volumes:" not in voice
    assert "VOICE_STT_PROVIDER=${VOICE_STT_PROVIDER:-vosk}" in voice
    assert "VOICE_TTS_PROVIDER=${VOICE_TTS_PROVIDER:-piper}" in voice
    assert "VOSK_MODEL_PATH=${VOSK_MODEL_PATH:-models/local-stt/vosk-en-us}" in voice
    assert "PIPER_MODEL_PATH=${PIPER_MODEL_PATH:-models/local-tts/voice.onnx}" in voice


def test_development_and_production_compose_define_health_dependencies():
    for name in ("docker-compose.yml", "docker-compose.prod.yml"):
        compose = (ROOT / name).read_text(encoding="utf-8")

        assert compose.count("healthcheck:") == 2
        assert "condition: service_healthy" in compose
        assert "urllib.request.urlopen('http://localhost:8000/health', timeout=2)" in compose
        assert 'test: ["CMD", "redis-cli", "ping"]' in compose
