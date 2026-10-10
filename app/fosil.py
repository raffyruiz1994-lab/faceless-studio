"""Motor Fosil — pipeline estilo Fósil Mental.

- Guion por escenas: {narration, visual_prompt, label} con gancho, bloques
  temáticos e infografía de cierre.
- Clips animados opcionales: Veo 3.1 Fast (Google AI Studio) o Kling (fal.ai).
- Las escenas sin clip usan ilustración fija con Ken Burns (ver fosil_assemble).
"""
from __future__ import annotations

import json
import os
import re
import time

FOSIL_SCRIPT_SYSTEM = """You are a scriptwriter for a faceless Spanish-language science/history
YouTube channel in the style of "Fósil Mental": ink-doodle + digital painting,
curiosity-driven, "mystery revealed" tone. Write in {language_name}.
Target pace: ~150 spoken words per minute.
Output ONLY valid JSON, no markdown fences, matching this schema:
{{"title": "...", "segments": [{{"narration": "...", "visual_prompt": "...", "label": "..."}}], "review_flags": ["..."]}}
Rules:
- narration: spoken text only. No stage directions, no speaker labels.
- Open with a striking hook in the first 2 sentences (an intriguing scene or a
  counterintuitive question), then develop in thematic blocks, then close with a
  one-paragraph conceptual summary.
- visual_prompt: ONE vivid visual per segment in this exact art direction:
  "ink doodle mixed with digital storybook painting, visible ink strokes, thick
  wobbly black outlines, small white stick figure with big expressive cartoon
  eyes when people appear, warm ochre and brown palette, paper texture".
  Describe the scene concretely (cross-sections and diagrams welcome).
- label: 1-3 UPPERCASE words for the on-screen marker label of that segment
  (e.g. "50°C", "MALQAF", "ADOBE"). Empty string "" if no label fits.
- Keep each segment 25-60 words so the visual rhythm stays high
  (one new illustration per narrated idea).
- Produce about {n_scenes} segments for a {minutes}-minute video.
- NEVER invent a bibliography. Unsure dates/numbers/names/quotes go in
  review_flags. Better to flag than to fabricate.
- Topic: {topic}"""

LANG_NAMES = {"es": "Spanish (español)", "en": "English", "pt": "Portuguese (português)"}

VEO_MODEL_FAST = "veo-3.1-fast-generate-001"
VEO_MODEL_LITE = "veo-3.1-lite-generate-001"


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("Model did not return JSON")
    return json.loads(m.group(0))


def generate_fosil_script(topic: str, language: str = "es", minutes: int = 3,
                          text_model: str = "gemini-2.5-flash",
                          api_key: str = "") -> dict:
    """Call the Gemini text API and return the validated fosil script dict."""
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured (see Settings).")
    from google import genai

    n_scenes = max(6, min(24, int(minutes * 60 / 50)))  # ~1 escena / 50s
    prompt = FOSIL_SCRIPT_SYSTEM.format(
        language_name=LANG_NAMES.get(language, "Spanish (español)"),
        n_scenes=n_scenes,
        minutes=minutes,
        topic=topic,
    )
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=text_model, contents=[prompt])
    script = _extract_json((response.text or "").strip())

    if not isinstance(script.get("segments"), list) or not script["segments"]:
        raise ValueError("Script has no segments")
    for seg in script["segments"]:
        for k in ("narration", "visual_prompt"):
            if k not in seg:
                raise ValueError(f"Segment missing {k}")
        seg.setdefault("label", "")
    script.setdefault("title", topic)
    script.setdefault("review_flags", [])
    script["word_count"] = sum(len(s["narration"].split()) for s in script["segments"])
    return script


# ---------------------------------------------------------------- clips ---

def _download(url: str, dest: str, headers: dict | None = None) -> None:
    import requests
    with requests.get(url, headers=headers or {}, timeout=120, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)


def generate_clip_veo(prompt: str, out_dir: str, api_key: str,
                      model: str = VEO_MODEL_FAST,
                      aspect: str = "16:9", duration_s: int = 8,
                      progress_cb=None) -> str:
    """Generate one animated clip with Veo via the Gemini API. Returns mp4 path."""
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured (see Settings).")
    from google import genai
    from google.genai import types

    os.makedirs(out_dir, exist_ok=True)
    client = genai.Client(api_key=api_key)
    op = client.models.generate_videos(
        model=model,
        prompt=prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio=aspect,
            number_of_videos=1,
        ),
    )
    start = time.time()
    while not op.done:
        if time.time() - start > 600:
            raise TimeoutError("Veo generation timed out")
        time.sleep(10)
        op = client.operations.get(op)
    vids = getattr(op.response, "generated_videos", None) or []
    if not vids:
        raise RuntimeError("Veo returned no video")
    gv = vids[0]
    dest = os.path.join(out_dir, f"clip_{int(time.time()*1000)%1000000:06d}.mp4")
    # google-genai>=1.x: video bytes via client.files.download or .video.uri
    video = getattr(gv, "video", gv)
    uri = getattr(video, "uri", None)
    if uri:
        _download(uri, dest)
    else:
        data = getattr(video, "video_bytes", None)
        if not data:
            raise RuntimeError("Veo returned no downloadable video bytes")
        with open(dest, "wb") as f:
            f.write(data)
    if progress_cb:
        progress_cb()
    return dest


def generate_clip_falai(prompt: str, out_dir: str, api_key: str,
                        model: str = "fal-ai/kling-video/v3/standard/text-to-video",
                        aspect: str = "16:9", duration_s: int = 10,
                        progress_cb=None) -> str:
    """Generate one animated clip via fal.ai queue API. Returns mp4 path."""
    if not api_key:
        raise RuntimeError("FAL_API_KEY is not configured (see Settings).")
    import requests

    os.makedirs(out_dir, exist_ok=True)
    headers = {"Authorization": f"Key {api_key}"}
    body = {"prompt": prompt, "aspect_ratio": aspect, "duration": str(duration_s)}
    r = requests.post(f"https://queue.fal.run/{model}", headers=headers,
                      json=body, timeout=30)
    r.raise_for_status()
    req_id = r.json().get("request_id")
    if not req_id:
        raise RuntimeError(f"fal.ai did not return a request_id: {r.json()}")

    start = time.time()
    while True:
        s = requests.get(f"https://queue.fal.run/{model}/requests/{req_id}/status",
                         headers=headers, timeout=30).json().get("status")
        if s == "COMPLETED":
            break
        if s == "FAILED":
            raise RuntimeError(f"fal.ai video generation failed ({req_id})")
        if time.time() - start > 900:
            raise TimeoutError(f"fal.ai video timed out ({req_id})")
        time.sleep(5)

    data = requests.get(f"https://queue.fal.run/{model}/requests/{req_id}",
                        headers=headers, timeout=30).json()
    video = data.get("video") or {}
    url = video.get("url")
    if not url:
        raise RuntimeError(f"fal.ai returned no video URL ({req_id})")
    dest = os.path.join(out_dir, f"clip_{req_id[:8]}.mp4")
    _download(url, dest)
    if progress_cb:
        progress_cb()
    return dest


CLIP_GENERATORS = {
    "veo": generate_clip_veo,
    "falai": generate_clip_falai,
}

# Coste estimado por segundo (USD) — verificar precios vigentes
CLIP_COST_PER_SEC = {"veo": 0.10, "falai": 0.084}
CLIP_SECONDS = {"veo": 8, "falai": 10}
