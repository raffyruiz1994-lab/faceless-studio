"""DRAFT (uncommitted) — Stage 2 image generation via fal.ai.

Pending Rafael confirming his 'faia' API is fal.ai. Do NOT commit/push or
wire into the pipeline until he confirms.

Implements the same generate_images() signature as app/images.py so the
pipeline can dispatch between providers ("gemini" | "falai") without
changing the rest of the flow.

fal.ai queue REST API (verified Oct 7, 2026 against public docs):
  POST https://queue.fal.run/{model_id}        -> {"request_id": ...}
  GET  .../requests/{request_id}/status        -> {"status": "IN_QUEUE"|"IN_PROGRESS"|"COMPLETED"|"FAILED"}
  GET  .../requests/{request_id}               -> {"images": [{"url": "..."}], ...}
  Header on every request:  Authorization: Key <FAL_KEY>
"""
from __future__ import annotations

import os
import time

import requests

from ..images import STYLES

QUEUE_BASE = "https://queue.fal.run"

IMAGE_MODELS = {
    "fal-ai/flux/dev": {
        "label": "FLUX Dev (alta calidad)",
        "image_size": "landscape_16_9",
    },
    "fal-ai/nano-banana": {
        "label": "Nano Banana (vía fal.ai)",
    },
}

_POLL_INTERVAL_FIRST = 3   # seconds, for the first 30s
_POLL_INTERVAL_AFTER = 5    # seconds afterwards
_POLL_TIMEOUT = 600         # 10 minutes per image


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Key {api_key}"}


def _submit(prompt: str, api_key: str, model: str) -> str:
    body: dict = {"prompt": prompt}
    image_size = IMAGE_MODELS[model].get("image_size")
    if image_size:
        body["image_size"] = image_size
    resp = requests.post(f"{QUEUE_BASE}/{model}", headers=_headers(api_key),
                         json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "request_id" not in data:
        raise RuntimeError(f"fal.ai did not return a request_id: {data}")
    return data["request_id"]


def _wait_result(request_id: str, api_key: str, model: str) -> str:
    """Poll until the image is ready; return its download URL."""
    start = time.time()
    while True:
        resp = requests.get(
            f"{QUEUE_BASE}/{model}/requests/{request_id}/status",
            headers=_headers(api_key), timeout=30)
        resp.raise_for_status()
        status = resp.json().get("status")
        if status == "COMPLETED":
            break
        if status == "FAILED":
            raise RuntimeError(f"fal.ai generation failed (request {request_id})")
        if time.time() - start > _POLL_TIMEOUT:
            raise TimeoutError(f"fal.ai generation timed out (request {request_id})")
        time.sleep(_POLL_INTERVAL_FIRST if time.time() - start < 30
                   else _POLL_INTERVAL_AFTER)

    resp = requests.get(f"{QUEUE_BASE}/{model}/requests/{request_id}",
                        headers=_headers(api_key), timeout=30)
    resp.raise_for_status()
    images = resp.json().get("images") or []
    if not images or "url" not in images[0]:
        raise RuntimeError(f"fal.ai returned no image URL (request {request_id})")
    return images[0]["url"]


def generate_images(script: dict, out_dir: str, api_key: str,
                    image_model: str = "fal-ai/flux/dev",
                    style: str = "stick",
                    progress_cb=None) -> list[str]:
    """Generate one 16:9 image per script segment via fal.ai.

    Same signature/contract as app/images.py:generate_images.
    """
    if not api_key:
        raise RuntimeError("FAL_API_KEY is not configured (see Settings).")
    if image_model not in IMAGE_MODELS:
        raise ValueError(f"Unknown fal.ai image model: {image_model}")
    suffix = STYLES.get(style, STYLES["stick"])["suffix"]

    os.makedirs(out_dir, exist_ok=True)
    paths: list[str] = []
    segments = script["segments"]
    for i, seg in enumerate(segments):
        prompt = seg["image_prompt"] + suffix
        request_id = _submit(prompt, api_key, image_model)
        url = _wait_result(request_id, api_key, image_model)
        dest = os.path.join(out_dir, f"img_{i:03d}.png")
        with requests.get(url, timeout=60, stream=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
        paths.append(dest)
        if progress_cb:
            progress_cb(i + 1, len(segments))
    return paths
