"""Stage 3 — Narration via Fish Audio TTS.

POST https://api.fish.audio/v1/tts
Headers: Authorization: Bearer <KEY>, model: s2.1-pro
Body: {"text", "reference_id" (voice id, may be ""), "format": "mp3",
       "mp3_bitrate": 192, "normalize": true, "latency": "normal"}
Returns raw mp3 bytes. ~$15 per 1M UTF-8 bytes.

Voice IDs: find them on fish.audio (voice library / your cloned voices).
An empty reference_id uses the Fish default voice.
"""
from __future__ import annotations

import os
import subprocess

FISH_TTS_URL = "https://api.fish.audio/v1/tts"
FISH_MODEL = "s2.1-pro"
COST_PER_1M_BYTES = 15.0


def _mp3_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def synthesize_segments(script: dict, out_dir: str, api_key: str,
                        voice_id: str = "", progress_cb=None) -> list[dict]:
    """Synthesize each segment's narration. Returns [{path, duration}]."""
    if not api_key:
        raise RuntimeError("FISH_AUDIO_API_KEY is not configured (see Settings).")
    import requests

    os.makedirs(out_dir, exist_ok=True)
    results: list[dict] = []
    segments = script["segments"]
    for i, seg in enumerate(segments):
        body = {
            "text": seg["narration"],
            "format": "mp3",
            "mp3_bitrate": 192,
            "normalize": True,
            "latency": "normal",
        }
        if voice_id:
            body["reference_id"] = voice_id
        resp = requests.post(
            FISH_TTS_URL,
            headers={"Authorization": f"Bearer {api_key}", "model": FISH_MODEL},
            json=body, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"Fish Audio error {resp.status_code}: {resp.text[:300]}")
        dest = os.path.join(out_dir, f"vox_{i:03d}.mp3")
        with open(dest, "wb") as f:
            f.write(resp.content)
        results.append({"path": dest, "duration": _mp3_duration(dest)})
        if progress_cb:
            progress_cb(i + 1, len(segments))
    return results


def estimate_cost_usd(total_text: str) -> float:
    return len(total_text.encode("utf-8")) / 1_000_000 * COST_PER_1M_BYTES
