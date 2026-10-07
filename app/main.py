"""Faceless Studio — FastAPI backend."""
from __future__ import annotations

import json
import os
import re
import threading
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import demo as demo_mod
from . import ideas as ideas_mod
from . import pipeline as pipeline_mod
from .settings_store import get_public_settings, get_settings, save_settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_ROOT = os.path.join(BASE_DIR, "jobs")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title="Faceless Studio")


class JobSpec(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    language: str = "es"
    minutes: int = Field(default=16, ge=1, le=60)
    image_model: str = ""
    voice_id: str = ""
    style: str = "stick"
    subtitles: bool = True
    demo: bool = False


class IdeasRequest(BaseModel):
    niche: str = "historia"
    count: int = Field(default=8, ge=3, le=12)
    language: str = "es"
    avoid: str = ""


class SettingsPatch(BaseModel):
    gemini_api_key: str = ""
    fish_audio_api_key: str = ""
    fish_voice_id: str = ""
    image_model: str = ""
    text_model: str = ""


def _read_status(job_id: str) -> dict:
    path = os.path.join(JOBS_ROOT, job_id, "status.json")
    if not os.path.exists(path):
        raise HTTPException(404, "job not found")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.post("/api/jobs")
def create_job(spec: JobSpec):
    job_id = uuid.uuid4().hex[:12]
    job_dir = os.path.join(JOBS_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)
    payload = spec.model_dump()
    if spec.demo:
        t = threading.Thread(target=demo_mod.run_demo,
                             args=(JOBS_ROOT, job_id, payload), daemon=True)
    else:
        t = threading.Thread(target=pipeline_mod.run_job,
                             args=(job_id, JOBS_ROOT, payload), daemon=True)
    t.start()
    return {"id": job_id}


@app.get("/api/jobs")
def list_jobs():
    out = []
    if os.path.isdir(JOBS_ROOT):
        for jid in sorted(os.listdir(JOBS_ROOT), reverse=True):
            try:
                out.append(_read_status(jid))
            except Exception:
                pass
    return {"jobs": out}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    return _read_status(job_id)


@app.get("/api/jobs/{job_id}/video")
def job_video(job_id: str):
    st = _read_status(job_id)
    if st.get("state") != "done":
        raise HTTPException(409, "video not ready")
    path = os.path.join(JOBS_ROOT, job_id, st.get("output", "output.mp4"))
    if not os.path.exists(path):
        raise HTTPException(404, "video file missing")
    return FileResponse(path, media_type="video/mp4",
                        filename=f"faceless-{job_id}.mp4")


@app.post("/api/ideas")
def suggest_ideas(req: IdeasRequest):
    settings = get_settings()
    try:
        ideas = ideas_mod.suggest_ideas(
            req.niche, req.count, req.language, req.avoid,
            settings.get("text_model", "gemini-2.5-flash"),
            settings.get("gemini_api_key", ""))
    except Exception as e:  # noqa: BLE001 — surfaced to the UI
        raise HTTPException(400, str(e)[:300])
    return {"ideas": ideas}


@app.get("/api/settings")
def read_settings():
    return get_public_settings()


@app.post("/api/settings")
def write_settings(patch: SettingsPatch):
    # Never log or return key values.
    return save_settings(patch.model_dump())


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(STATIC_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
