"""Pipeline orchestrator: runs the 4 stages for a job directory."""
from __future__ import annotations

import json
import os
import time

from . import assemble, images as images_mod, script_gen, voice as voice_mod
from .settings_store import get_settings


def _write_status(job_dir: str, status: dict) -> None:
    tmp = os.path.join(job_dir, "status.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)
    os.replace(tmp, os.path.join(job_dir, "status.json"))


def estimate_cost(script: dict, image_model: str) -> dict:
    n_images = len(script["segments"])
    per_1k = images_mod.IMAGE_MODELS.get(image_model, {"cost_per_1k": 0.067})["cost_per_1k"]
    img_cost = n_images * per_1k
    text = " ".join(s["narration"] for s in script["segments"])
    voice_cost = voice_mod.estimate_cost_usd(text)
    return {
        "images": n_images,
        "image_cost_usd": round(img_cost, 2),
        "voice_bytes": len(text.encode("utf-8")),
        "voice_cost_usd": round(voice_cost, 2),
        "total_usd": round(img_cost + voice_cost, 2),
    }


def write_review_checklist(job_dir: str, script: dict, cost: dict) -> str:
    """Human review gate file — must be checked before any YouTube upload."""
    path = os.path.join(job_dir, "REVIEW_CHECKLIST.md")
    flags = script.get("review_flags") or ["(none flagged — still spot-check dates and names)"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Human review gate — complete BEFORE uploading to YouTube\n\n")
        f.write("YouTube's 'inauthentic content' policy demonetizes zero-review AI factory\n")
        f.write("channels. Watch the full video once and confirm each item:\n\n")
        f.write("- [ ] Narration has no mispronunciations or robotic glitches\n")
        f.write("- [ ] No factually wrong dates, names, or numbers\n")
        f.write("- [ ] Images match the narration (no anachronisms, no gibberish text in frames)\n")
        f.write("- [ ] Subtitles are readable and correctly timed\n")
        f.write("- [ ] Music bed is subtle and does not drown the voice\n")
        f.write("- [ ] Title, description and thumbnail prepared (not auto-generated)\n")
        f.write("\n## Claims flagged by the script model — verify these:\n\n")
        for fl in flags:
            f.write(f"- [ ] {fl}\n")
        f.write(f"\n## Cost\nEstimated API cost for this video: ${cost['total_usd']:.2f} "
                f"(images ${cost['image_cost_usd']:.2f} + voice ${cost['voice_cost_usd']:.2f})\n")
    return path


def run_job(job_id: str, jobs_root: str, spec: dict) -> None:
    """Run all stages. spec: {topic, language, minutes, image_model, voice_id}."""
    job_dir = os.path.join(jobs_root, job_id)
    os.makedirs(job_dir, exist_ok=True)
    settings = get_settings()

    status = {"id": job_id, "state": "running", "stage": "script",
              "progress": 0.0, "detail": "", "error": None,
              "created_at": time.time(), "spec": {k: v for k, v in spec.items()}}
    _write_status(job_dir, status)

    def set_stage(stage, progress, detail=""):
        status.update({"stage": stage, "progress": progress, "detail": detail})
        _write_status(job_dir, status)

    try:
        # 1. script
        set_stage("script", 0.02, "Generating script…")
        script = script_gen.generate_script(
            spec["topic"], spec.get("language", "es"), spec.get("minutes", 16),
            settings.get("text_model", "gemini-2.5-flash"),
            settings.get("gemini_api_key", ""))
        with open(os.path.join(job_dir, "script.json"), "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)

        cost = estimate_cost(script, spec.get("image_model") or settings["image_model"])
        status["cost_estimate"] = cost
        _write_status(job_dir, status)

        # 2. images
        style = spec.get("style", "stick")
        style_label = images_mod.STYLES.get(style, images_mod.STYLES["stick"])["label"]
        set_stage("images", 0.10, f"Generating {style_label} images…")
        img_dir = os.path.join(job_dir, "images")
        img_paths = images_mod.generate_images(
            script, img_dir, settings["gemini_api_key"],
            spec.get("image_model") or settings["image_model"],
            style=style,
            progress_cb=lambda d, t: set_stage("images", 0.10 + 0.35 * d / t,
                                               f"Image {d}/{t}"))

        # 3. voice
        set_stage("voice", 0.48, "Synthesizing narration…")
        vox_dir = os.path.join(job_dir, "voice")
        audios = voice_mod.synthesize_segments(
            script, vox_dir, settings["fish_audio_api_key"],
            spec.get("voice_id") or settings.get("fish_voice_id", ""),
            progress_cb=lambda d, t: set_stage("voice", 0.48 + 0.22 * d / t,
                                                f"Voice {d}/{t}"))

        # 4. assemble
        set_stage("assemble", 0.72, "Rendering video…")
        out = os.path.join(job_dir, "output.mp4")
        result = assemble.assemble(
            job_dir, script["segments"], img_paths, audios, out,
            progress_cb=lambda d, t, stage_detail="": set_stage(
                "assemble", 0.72 + 0.26 * d / t, f"Segment {d}/{t}"))

        write_review_checklist(job_dir, script, cost)
        status.update({"state": "done", "stage": "done", "progress": 1.0,
                       "detail": "", "duration": result["duration"],
                       "output": "output.mp4"})
        _write_status(job_dir, status)
    except Exception as e:  # noqa: BLE001 — surfaced to the UI
        status.update({"state": "error", "error": str(e)[:500]})
        _write_status(job_dir, status)
