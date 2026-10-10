"""Ensamblaje estilo Fósil Mental con ffmpeg.

Por escena: clip de video (si hay) o Ken Burns sobre ilustración fija.
Subtítulos .srt quemados estilo canal (línea inferior, fondo semitransparente)
y rótulo marcador en mayúsculas arriba.
Salida: 1920x1080, h264 + aac, faststart.
"""
from __future__ import annotations

import os
import subprocess

W, H, FPS = 1920, 1080, 30
NARR_DELAY = 0.6   # la narración entra 0.6s después del corte
IMG_TAIL = 1.2     # imagen fija se sostiene 1.2s tras la narración

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SUB_STYLE = ("FontName=DejaVu Sans,FontSize=26,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H80000000,BackColour=&H99000000,BorderStyle=1,"
             "Outline=2,Shadow=0,Alignment=2,MarginV=48")


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd[:6])}...\n{r.stderr[-2000:]}")


def _probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _srt_time(sec: float) -> str:
    h = int(sec // 3600); m = int((sec % 3600) // 60)
    s = int(sec % 60); ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _chunk_text(text: str, max_words: int = 12) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]


def write_scene_srt(narration: str, srt_path: str) -> float:
    """Subtítulos proporcionales al texto. Devuelve duración de la narración."""
    chunks = _chunk_text(narration)
    total = sum(len(c) for c in chunks) or 1
    # duración estimada a 150 ppm
    dur = max(2.0, len(narration.split()) / 150 * 60)
    t = NARR_DELAY
    lines = []
    for i, ch in enumerate(chunks, 1):
        end = t + dur * len(ch) / total
        if i == len(chunks):
            end = NARR_DELAY + dur
        lines.append(f"{i}\n{_srt_time(t)} --> {_srt_time(end)}\n{ch}\n")
        t = end
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return dur


def _drawtext(label: str) -> str:
    if not label:
        return ""
    safe = label.replace("'", "").replace(":", "\\:")
    return (f",drawtext=fontfile={FONT_BOLD}:text='{safe}':fontsize=56:"
            f"fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=60")


def render_scene(visual: dict, audio_path: str, audio_dur: float,
                 narration: str, label: str, srt_path: str,
                 dest: str, zoom_in: bool, subtitles: bool = True) -> float:
    """Renderiza una escena. Devuelve su duración total."""
    write_scene_srt(narration, srt_path)
    sub = f",subtitles='{srt_path}':force_style='{SUB_STYLE}'" if subtitles else ""
    dt = _drawtext(label)

    if visual["kind"] == "clip":
        total = _probe_duration(visual["path"])
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},setsar=1,fps={FPS}{sub}{dt}")
        _run([
            "ffmpeg", "-y", "-v", "error",
            "-i", visual["path"], "-i", audio_path,
            "-filter_complex",
            f"[0:v]{vf}[v];"
            f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            f"adelay={int(NARR_DELAY*1000)}|{int(NARR_DELAY*1000)},"
            f"apad=whole_dur={total:.2f},atrim=0:{total:.2f}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-t", f"{total:.2f}", dest,
        ])
        return total

    # imagen fija con Ken Burns
    total = audio_dur + IMG_TAIL
    frames = max(1, int(total * FPS))
    z = f"1+0.12*on/{frames}" if zoom_in else f"1.12-0.12*on/{frames}"
    vf = (f"scale=2560:1440,"
          f"zoompan=z='{z}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"s={W}x{H}:fps={FPS},setsar=1{sub}{dt}")
    _run([
        "ffmpeg", "-y", "-v", "error",
        "-i", visual["path"], "-i", audio_path,
        "-filter_complex",
        f"[0:v]{vf}[v];"
        f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,"
        f"adelay={int(NARR_DELAY*1000)}|{int(NARR_DELAY*1000)},"
        f"apad=whole_dur={total:.2f},atrim=0:{total:.2f}[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-t", f"{total:.2f}", dest,
    ])
    return total


def assemble_fosil(job_dir: str, scenes: list[dict], visuals: list[dict],
                   audios: list[dict], output_path: str,
                   subtitles: bool = True, progress_cb=None) -> dict:
    """
    scenes:  [{narration, label}]
    visuals: [{kind: "clip"|"image", path}] — uno por escena
    audios:  [{path, duration}] — uno por escena
    """
    seg_dir = os.path.join(job_dir, "segments")
    os.makedirs(seg_dir, exist_ok=True)
    subs_dir = os.path.join(job_dir, "subs")
    os.makedirs(subs_dir, exist_ok=True)

    seg_files = []
    total = 0.0
    n = len(scenes)
    for i in range(n):
        dest = os.path.join(seg_dir, f"seg_{i:03d}.mp4")
        srt = os.path.join(subs_dir, f"s{i}.srt")
        dur = render_scene(visuals[i], audios[i]["path"], audios[i]["duration"],
                           scenes[i]["narration"], scenes[i].get("label", ""),
                           srt, dest, zoom_in=(i % 2 == 0),
                           subtitles=subtitles)
        total += dur
        seg_files.append(dest)
        if progress_cb:
            progress_cb(i + 1, n)

    lst = os.path.join(job_dir, "concat.txt")
    with open(lst, "w") as f:
        for p in seg_files:
            f.write(f"file '{os.path.abspath(p)}'\n")
    try:
        _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
              "-i", lst, "-c", "copy", output_path])
    except RuntimeError:
        _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
              "-i", lst, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
              "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", output_path])
    return {"output": output_path, "duration": total, "segments": n}
