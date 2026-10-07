"""Stage 2 — Cinematic image generation via Nano Banana 2 (Gemini image API).

Model: gemini-3.1-flash-image-preview (~$0.067 per 1K image).
Optional quality model: gemini-3-pro-image-preview ($0.134).
One 16:9 cinematic still per script segment.
"""
from __future__ import annotations

import os

STYLES = {
    "stick": {
        "label": "Stick figure (vectorial)",
        "suffix": (
            ", flat vector cartoon illustration in stick-figure style: simple characters "
            "with round white heads and thin black line bodies, flat muted earthy colors, "
            "simple cartoon backgrounds, 2D animated documentary still, "
            "16:9 widescreen composition, no text, no watermark"
        ),
    },
    "cinematic": {
        "label": "Cinematográfico",
        "suffix": (
            ", cinematic documentary film still, dramatic lighting, rich detail, "
            "16:9 widescreen composition, no text, no watermark, no people close-ups "
            "unless essential"
        ),
    },
}

# Backwards-compat alias
STYLE_SUFFIX = STYLES["cinematic"]["suffix"]

IMAGE_MODELS = {
    "gemini-3.1-flash-image-preview": {"label": "Nano Banana 2 (Flash)", "cost_per_1k": 0.067},
    "gemini-3-pro-image-preview": {"label": "Nano Banana Pro", "cost_per_1k": 0.134},
}


def _save_inline_image(response, dest_path: str) -> bool:
    """Extract the first inline image from a Gemini response and save it."""
    for cand in getattr(response, "candidates", []) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", []) or []:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                with open(dest_path, "wb") as f:
                    f.write(inline.data)
                return True
    return False


def generate_images(script: dict, out_dir: str, api_key: str,
                    image_model: str = "gemini-3.1-flash-image-preview",
                    style: str = "stick",
                    progress_cb=None) -> list[str]:
    """Generate one image per segment. Returns list of image paths."""
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured (see Settings).")
    if image_model not in IMAGE_MODELS:
        raise ValueError(f"Unknown image model: {image_model}")
    suffix = STYLES.get(style, STYLES["stick"])["suffix"]
    from google import genai

    os.makedirs(out_dir, exist_ok=True)
    client = genai.Client(api_key=api_key)
    paths: list[str] = []
    segments = script["segments"]
    for i, seg in enumerate(segments):
        prompt = seg["image_prompt"] + suffix
        response = client.models.generate_content(model=image_model, contents=[prompt])
        dest = os.path.join(out_dir, f"img_{i:03d}.png")
        if not _save_inline_image(response, dest):
            raise RuntimeError(f"No image returned for segment {i}")
        paths.append(dest)
        if progress_cb:
            progress_cb(i + 1, len(segments))
    return paths
