"""Stage 1 — Script generation via the Gemini text API.

Produces structured JSON for the documentary:
{
  "title": "...",
  "thesis": "one-sentence poetic thesis, like 'the history of X is a story written by Y'",
  "segments": [
     {"narration": "spoken text (no stage directions)",
      "image_prompt": "cinematic visual description for this segment",
      "duration_hint": "slow|medium"}
  ],
  "review_flags": ["claims the model is unsure about and a human should verify"]
}

HONESTY RULE: the model is instructed NOT to invent a sources list. Anything it
is not sure about (dates, numbers, quotes, attributions) goes into review_flags
for the human review gate. Never present review_flags content as verified.
"""
from __future__ import annotations

import json
import re

SCRIPT_SYSTEM = """You are a documentary scriptwriter for a faceless cinematic history channel.
Write in {language_name}. Target pace: ~150 spoken words per minute.
Output ONLY valid JSON, no markdown fences, matching this schema:
{{"title": "...", "thesis": "...", "segments": [{{"narration": "...", "image_prompt": "...", "duration_hint": "slow"}}], "review_flags": ["..."]}}
Rules:
- narration: spoken documentary text only. No "[music]", no speaker labels, no parentheses directions.
- Open with a poetic thesis hook (one striking idea that frames the whole story), then tell the story chronologically with curiosity gaps.
- image_prompt: one vivid cinematic visual per segment, e.g. "aerial view of ancient stone city at dawn, mist, cinematic documentary still".
- Keep each segment 60-110 words so pacing stays tight.
- Produce about {n_segments} segments for a {minutes}-minute video.
- NEVER invent a bibliography or sources list. If you are unsure about a date, number, name, quote or attribution, put the exact claim in review_flags instead of stating it as certain. It is better to flag than to fabricate.
- Topic: {topic}"""

LANG_NAMES = {"es": "Spanish (español)", "en": "English", "pt": "Portuguese (português)"}


def _extract_json(text: str) -> dict:
    """Pull the first {...} JSON object out of model output."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("Model did not return JSON")
    return json.loads(m.group(0))


def generate_script(topic: str, language: str = "es", minutes: int = 16,
                    text_model: str = "gemini-2.5-flash", api_key: str = "") -> dict:
    """Call the Gemini text API and return the validated script dict."""
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured (see Settings).")
    from google import genai

    n_segments = max(4, int(minutes * 150 / 85))  # ~85 words per segment
    prompt = SCRIPT_SYSTEM.format(
        language_name=LANG_NAMES.get(language, "Spanish (español)"),
        n_segments=n_segments,
        minutes=minutes,
        topic=topic,
    )
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=text_model, contents=[prompt])
    text = (response.text or "").strip()
    script = _extract_json(text)

    # Validate shape
    if not isinstance(script.get("segments"), list) or not script["segments"]:
        raise ValueError("Script has no segments")
    for seg in script["segments"]:
        if "narration" not in seg or "image_prompt" not in seg:
            raise ValueError("Segment missing narration/image_prompt")
        seg.setdefault("duration_hint", "slow")
    script.setdefault("title", topic)
    script.setdefault("thesis", "")
    script.setdefault("review_flags", [])
    script["word_count"] = sum(len(s["narration"].split()) for s in script["segments"])
    return script
