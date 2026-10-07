"""AI-suggested video ideas for the channel.

Asks the Gemini text model for fresh, high-retention documentary topics and
returns structured ideas the user can turn into jobs with one tap.
"""
from __future__ import annotations

import json
import re

IDEAS_PROMPT = """You are a YouTube strategist for a faceless history documentary channel.
The channel makes long-form (10-20 min) stick-figure animated documentaries in {language_name},
in the style of "the entire history of X in Y minutes" videos.

Suggest {count} fresh video ideas about {niche}. Mix well-known topics with surprising
angles and lesser-known stories with viral potential. Avoid ideas already listed: {avoid}.

Output ONLY valid JSON, no markdown fences:
{{"ideas": [{{"title": "catchy Spanish title", "hook": "one-sentence opening hook", "angle": "why this will retain viewers (one line)"}}]}}
Rules:
- titles in {language_name}, under 70 characters, curiosity-driven, no clickbait lies.
- Each idea must be a real historical topic that can sustain 10+ minutes.
- Vary eras and regions; at least 2 ideas from non-European history."""

LANG_NAMES = {"es": "Spanish (español)", "en": "English", "pt": "Portuguese (português)"}


def suggest_ideas(niche: str = "historia", count: int = 8, language: str = "es",
                  avoid: str = "", text_model: str = "gemini-2.5-flash",
                  api_key: str = "") -> list[dict]:
    """Return [{title, hook, angle}]."""
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured (see Settings).")
    from google import genai

    prompt = IDEAS_PROMPT.format(
        language_name=LANG_NAMES.get(language, "Spanish (español)"),
        count=max(3, min(count, 12)),
        niche=niche,
        avoid=avoid or "(none)",
    )
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=text_model, contents=[prompt])
    text = (response.text or "").strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("Model did not return JSON")
    data = json.loads(m.group(0))
    ideas = data.get("ideas") or []
    return [{"title": i.get("title", ""), "hook": i.get("hook", ""),
             "angle": i.get("angle", "")} for i in ideas if i.get("title")]
