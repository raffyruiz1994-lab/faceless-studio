"""Demo mode: runs the full local pipeline WITHOUT any API keys.

- Script: small built-in demo script (Spanish).
- Images: PIL-generated cinematic-style placeholders (gradient skies, silhouettes).
- Audio: silent track with word-count-estimated durations (words / 150 wpm).
- Assembly: identical to the real pipeline (Ken Burns, karaoke subtitles, music).

Proves the local toolchain works end-to-end before configuring paid APIs.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import time

from PIL import Image, ImageDraw, ImageFont

from . import assemble, fosil_assemble

DEMO_SCRIPT = {
    "title": "Demo: La caída de Constantinopla",
    "thesis": "Un imperio de mil años cayó en un solo amanecer.",
    "segments": [
        {"narration": (
            "Durante más de mil años, Constantinopla fue la ciudad más rica y mejor "
            "defendida del mundo. Sus murallas triples habían resistido cada asedio. "
            "Pero en la primavera de 1453, un sultán de veintiún años llegó con un "
            "ejército como nunca se había visto."),
         "image_prompt": "demo", "duration_hint": "slow"},
        {"narration": (
            "Mehmed Segundo arrastró sus barcos por tierra, rodeando la cadena que "
            "protegía el Cuerno de Oro. Sus cañones gigantes, los más grandes jamás "
            "construidos, golpearon las murallas durante semanas sin descanso."),
         "image_prompt": "demo", "duration_hint": "slow"},
        {"narration": (
            "El veintinueve de mayo, al amanecer, los otomanos entraron por una "
            "puerta olvidada. Constantino Onceavo murió luchando entre sus hombres. "
            "Así terminó el Imperio Bizantino, y comenzó una nueva era."),
         "image_prompt": "demo", "duration_hint": "slow"},
    ],
    "review_flags": ["(demo — verify all dates before real use)"],
}

WPM = 150


def _font(size: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make_placeholder_image(dest: str, seed: int, title: str, banner: bool = True) -> None:
    """Cinematic-style gradient placeholder with silhouette shapes."""
    rng = random.Random(seed)
    w, h = 1920, 1080
    top = (rng.randint(8, 30), rng.randint(10, 35), rng.randint(40, 80))
    bottom = (rng.randint(120, 200), rng.randint(60, 110), rng.randint(30, 70))
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        f = y / h
        px_col = tuple(int(top[c] + (bottom[c] - top[c]) * f) for c in range(3))
        for x in range(w):
            px[x, y] = px_col
    d = ImageDraw.Draw(img)
    # sun / moon glow
    sx, sy = rng.randint(300, 1600), rng.randint(150, 450)
    for r in range(180, 0, -4):
        d.ellipse([sx - r, sy - r, sx + r, sy + r],
                  fill=(min(255, top[0] + 120), min(255, top[1] + 100), 90))
    # mountain silhouettes
    base = h
    for layer in range(3):
        pts = [(0, base)]
        x = 0
        yb = base - rng.randint(120, 320) - layer * 60
        while x < w:
            pts.append((x, yb + rng.randint(-70, 70)))
            x += rng.randint(120, 320)
        pts.append((w, base))
        shade = max(0, 25 - layer * 8)
        d.polygon(pts, fill=(shade, shade, shade + 12))
    # title card
    fnt = _font(72)
    d.text((w // 2, h - 140), title, font=fnt, fill=(235, 235, 235), anchor="mm",
           stroke_width=2, stroke_fill=(0, 0, 0))
    if banner:
        d.text((w // 2, 90), "MODO DEMO — sin APIs", font=_font(40),
               fill=(255, 200, 80), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
    img.save(dest)


def make_silent_audio(dest: str, duration: float) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"anullsrc=r=44100:cl=stereo:d={duration:.2f}",
         "-c:a", "libmp3lame", "-b:a", "128k", dest], check=True)


def estimate_duration(narration: str) -> float:
    return max(3.0, len(narration.split()) / WPM * 60.0)


FOSIL_DEMO_SCRIPT = {
    "title": "Demo Fosil: Cómo vencían el calor sin electricidad",
    "segments": [
        {"narration": ("El desierto egipcio supera los cincuenta grados. "
                       "Sin electricidad ni ventiladores, y aun así prosperaban. ¿Cómo?"),
         "visual_prompt": "demo", "label": "50°C"},
        {"narration": ("El secreto estaba en las paredes: adobe de medio metro. "
                       "El barro traga el calor del día y lo suelta de noche."),
         "visual_prompt": "demo", "label": "ADOBE"},
        {"narration": ("Y el malqaf, una torre atrapavientos, llevaba la brisa fresca "
                       "al interior de la casa. Aire en movimiento sin un solo motor."),
         "visual_prompt": "demo", "label": "MALQAF"},
    ],
    "review_flags": ["(demo fosil — verify all claims before real use)"],
}


def run_fosil_demo(jobs_root: str, job_id: str, spec: dict | None = None) -> None:
    """Demo del motor Fosil: sin APIs, con ensamblaje estilo canal."""
    job_dir = os.path.join(jobs_root, job_id)
    os.makedirs(job_dir, exist_ok=True)
    spec = dict(spec or {})
    spec.setdefault("demo", True)
    spec.setdefault("engine", "fosil")

    def set_status(state, stage, progress, detail="", error=None):
        s = {"id": job_id, "state": state, "stage": stage, "progress": progress,
             "detail": detail, "error": error, "created_at": time.time(),
             "engine": "fosil", "spec": spec,
             "cost_estimate": {"images": 0, "clips": 0, "image_cost_usd": 0,
                               "clip_cost_usd": 0, "voice_cost_usd": 0, "total_usd": 0}}
        with open(os.path.join(job_dir, "status.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)

    try:
        set_status("running", "images", 0.05, "Demo imágenes…")
        img_dir = os.path.join(job_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        visuals = []
        for i, seg in enumerate(FOSIL_DEMO_SCRIPT["segments"]):
            p = os.path.join(img_dir, f"img_{i:03d}.png")
            make_placeholder_image(p, seed=2000 + i,
                                   title=f"Escena {i + 1} · DEMO", banner=False)
            visuals.append({"kind": "image", "path": p})

        set_status("running", "voice", 0.35, "Demo audio…")
        vox_dir = os.path.join(job_dir, "voice")
        os.makedirs(vox_dir, exist_ok=True)
        audios = []
        for i, seg in enumerate(FOSIL_DEMO_SCRIPT["segments"]):
            dur = estimate_duration(seg["narration"])
            p = os.path.join(vox_dir, f"vox_{i:03d}.mp3")
            make_silent_audio(p, dur)
            audios.append({"path": p, "duration": dur})

        set_status("running", "assemble", 0.55, "Editando…")
        out = os.path.join(job_dir, "output.mp4")
        result = fosil_assemble.assemble_fosil(
            job_dir, FOSIL_DEMO_SCRIPT["segments"], visuals, audios, out,
            subtitles=spec.get("subtitles", True),
            progress_cb=lambda d, t: set_status(
                "running", "assemble", 0.55 + 0.43 * d / t, f"Escena {d}/{t}"))

        with open(os.path.join(job_dir, "REVIEW_CHECKLIST.md"), "w", encoding="utf-8") as f:
            f.write("# Demo Fosil checklist\n\nDemo render (placeholder images, silent audio).\n"
                    "Configure API keys in Settings for real production.\n")
        set_status("done", "done", 1.0, "")
        with open(os.path.join(job_dir, "status.json"), "r", encoding="utf-8") as f:
            s = json.load(f)
        s["duration"] = result["duration"]
        s["output"] = "output.mp4"
        with open(os.path.join(job_dir, "status.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except Exception as e:  # noqa: BLE001
        set_status("error", "error", 0.0, error=str(e)[:500])


def run_demo(jobs_root: str, job_id: str, spec: dict | None = None) -> None:
    if (spec or {}).get("engine", "fosil") == "fosil":
        return run_fosil_demo(jobs_root, job_id, spec)
    job_dir = os.path.join(jobs_root, job_id)
    os.makedirs(job_dir, exist_ok=True)
    spec = dict(spec or {})
    spec.setdefault("demo", True)
    spec.setdefault("topic", DEMO_SCRIPT["title"])

    def set_status(state, stage, progress, detail="", error=None):
        s = {"id": job_id, "state": state, "stage": stage, "progress": progress,
             "detail": detail, "error": error, "created_at": time.time(),
             "spec": spec,
             "cost_estimate": {"images": 0, "image_cost_usd": 0,
                               "voice_bytes": 0, "voice_cost_usd": 0, "total_usd": 0}}
        with open(os.path.join(job_dir, "status.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)

    try:
        set_status("running", "images", 0.05, "Demo images…")
        img_dir = os.path.join(job_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        img_paths = []
        for i, seg in enumerate(DEMO_SCRIPT["segments"]):
            p = os.path.join(img_dir, f"img_{i:03d}.png")
            make_placeholder_image(p, seed=1000 + i, title=f"Escena {i + 1}")
            img_paths.append(p)

        set_status("running", "voice", 0.35, "Demo audio…")
        vox_dir = os.path.join(job_dir, "voice")
        os.makedirs(vox_dir, exist_ok=True)
        audios = []
        for i, seg in enumerate(DEMO_SCRIPT["segments"]):
            dur = estimate_duration(seg["narration"])
            p = os.path.join(vox_dir, f"vox_{i:03d}.mp3")
            make_silent_audio(p, dur)
            audios.append({"path": p, "duration": dur})

        set_status("running", "assemble", 0.55, "Rendering…")
        out = os.path.join(job_dir, "output.mp4")
        result = assemble.assemble(
            job_dir, DEMO_SCRIPT["segments"], img_paths, audios, out,
            progress_cb=lambda d, t, stage_detail="": set_status(
                "running", "assemble", 0.55 + 0.43 * d / t, f"Segmento {d}/{t}"),
            subtitles=(spec or {}).get("subtitles", True))

        with open(os.path.join(job_dir, "REVIEW_CHECKLIST.md"), "w", encoding="utf-8") as f:
            f.write("# Demo checklist\n\nThis is a demo render (placeholder images, silent audio).\n"
                    "Configure API keys in Settings for real production.\n")
        set_status("done", "done", 1.0, "")
        # patch duration into status
        with open(os.path.join(job_dir, "status.json"), "r", encoding="utf-8") as f:
            s = json.load(f)
        s["duration"] = result["duration"]
        s["output"] = "output.mp4"
        with open(os.path.join(job_dir, "status.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except Exception as e:  # noqa: BLE001
        set_status("error", "error", 0.0, error=str(e)[:500])
