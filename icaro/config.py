"""Configuração local estrita, sem comandos de shell."""
import json
from pathlib import Path
from .commands import normalize
from .navigation import validate_url

DEFAULT = {
    "sites": {"youtube": "https://www.youtube.com", "github": "https://github.com"},
    "apps": {},
    "voice": {"model_path": "models/vosk-model-small-pt-0.3", "device": None},
}


def load_config(path: Path, *, required: bool = False) -> dict:
    data = json.loads(json.dumps(DEFAULT))
    if not path.exists() and not required:
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict) or set(raw) - set(DEFAULT):
            raise ValueError("Seções permitidas: sites, apps e voice.")
        for section in raw:
            if not isinstance(raw[section], dict):
                raise ValueError(f"{section} deve ser um objeto.")
        for section in ("sites", "apps"):
            seen = set()
            for name, value in raw.get(section, {}).items():
                key = normalize(name)
                if not key or key in seen or not isinstance(value, str) or not value.strip():
                    raise ValueError(f"Nome duplicado/vazio ou valor inválido em {section}.")
                seen.add(key)
                if section == "sites":
                    value = validate_url(value)
                elif Path(value).suffix.lower() != ".exe" or not Path(value).is_absolute():
                    raise ValueError("Aplicativos exigem caminho absoluto para arquivo .exe.")
                data[section][key] = value
        voice = raw.get("voice", {})
        if set(voice) - {"model_path", "device"}:
            raise ValueError("Opção de voz desconhecida.")
        if "model_path" in voice and (not isinstance(voice["model_path"], str) or not voice["model_path"].strip()):
            raise ValueError("model_path deve ser um caminho não vazio.")
        device = voice.get("device")
        if device is not None and (isinstance(device, bool) or not isinstance(device, (int, str)) or isinstance(device, int) and device < 0 or isinstance(device, str) and not device.strip()):
            raise ValueError("device deve ser null, índice não negativo ou nome do microfone.")
        data["voice"].update(voice)
        from .apps import ALIASES
        if set(data["sites"]) & (set(data["apps"]) | set(ALIASES) | {"navegador"}):
            raise ValueError("Nome de site conflita com aplicativo/navegador.")
        if "navegador" in data["apps"]:
            raise ValueError("O nome navegador é reservado.")
        return data
    except (OSError, ValueError) as error:
        raise ValueError(f"Configuração {path}: {error}") from error
