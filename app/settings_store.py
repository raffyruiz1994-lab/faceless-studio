"""Settings persistence. API keys are stored in a local JSON file (0600)
and are never logged or returned by the API."""
from __future__ import annotations

import json
import os
import threading

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.json")

_DEFAULTS = {
    "gemini_api_key": "",
    "fish_audio_api_key": "",
    "fish_voice_id": "",          # Fish Audio reference_id; empty = Fish default voice
    "image_model": "gemini-3.1-flash-image-preview",  # or gemini-3-pro-image-preview
    "text_model": "gemini-2.5-flash",
}

_lock = threading.Lock()


def _read_file() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_settings() -> dict:
    """Return settings merged over defaults. Never logs values."""
    with _lock:
        merged = dict(_DEFAULTS)
        merged.update(_read_file())
        return merged


def get_public_settings() -> dict:
    """Settings safe to show in the UI: keys are masked, never returned."""
    s = get_settings()
    return {
        "gemini_api_key_set": bool(s.get("gemini_api_key")),
        "fish_audio_api_key_set": bool(s.get("fish_audio_api_key")),
        "fish_voice_id": s.get("fish_voice_id", ""),
        "image_model": s.get("image_model", _DEFAULTS["image_model"]),
        "text_model": s.get("text_model", _DEFAULTS["text_model"]),
    }


def save_settings(patch: dict) -> dict:
    """Merge a partial update into settings.json. Only known keys are stored."""
    allowed = set(_DEFAULTS.keys())
    with _lock:
        current = _read_file()
        for k, v in (patch or {}).items():
            if k in allowed and isinstance(v, str):
                current[k] = v.strip()
        tmp = SETTINGS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        os.replace(tmp, SETTINGS_PATH)
        try:
            os.chmod(SETTINGS_PATH, 0o600)
        except OSError:
            pass
    return get_public_settings()
