"""Stage 4 — Assemble the documentary with ffmpeg.

Per segment: Ken Burns motion (zoompan, alternating zoom in/out) over the
cinematic image, timed to the narration audio (+0.4s tail).
Then: concat, mix a subtle numpy-synthesized ambient music bed, and burn
MODERN styled subtitles: .ass with word-by-word karaoke highlight
(word timing estimated proportionally by character length within each
segment's real audio duration).

Output: 1920x1080, h264 + aac, faststart.
"""
from __future__ import annotations

import os
import subprocess
import wave

import numpy as np

W, H, FPS = 1920, 1080, 30
SEG_TAIL = 0.4          # seconds of image held after narration ends
WORDS_PER_MIN = 150


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd[:6])}...\n{r.stderr[-2000:]}")


def _ass_time(sec: float) -> str:
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _escape_ass(text: str) -> str:
    return text.replace("{", "(").replace("}", ")").replace("\n", " ")


def build_subtitles(segments: list[dict], ass_path: str, single_line: bool = True) -> None:
    """Write a karaoke .ass file. segments: [{narration, start, duration}].

    single_line=True: modern viral style — one short line (~6 words) at a time,
    centered, with karaoke word-fill. single_line=False: full paragraph block.
    """
    style_line = (
        "Style: Modern,DejaVu Sans,84,&H0000FFFF,&H00FFFFFF,&H90000000,&H90000000,"
        "-1,0,0,0,100,100,0.5,0,1,3,1,2,60,60,110,1"
        if single_line else
        "Style: Modern,DejaVu Sans,64,&H0000FFFF,&H00FFFFFF,&H90000000,&H90000000,"
        "-1,0,0,0,100,100,0.5,0,1,3,1,2,60,60,110,1"
    )
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_line}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for seg in segments:
        words = [w for w in seg["narration"].split() if w]
        if not words:
            continue
        if single_line:
            groups = [words[i:i + 6] for i in range(0, len(words), 6)]
            total_chars = sum(len(w) for w in words) or 1
            t = seg["start"]
            for g in groups:
                g_chars = sum(len(w) for w in g) or 1
                g_dur = seg["duration"] * g_chars / total_chars
                chunks = []
                for w in g:
                    cs = max(1, int(g_dur * len(w) / g_chars * 100))  # centiseconds
                    chunks.append(f"{{\\kf{cs}}}{_escape_ass(w)}")
                lines.append(
                    f"Dialogue: 0,{_ass_time(t)},{_ass_time(t + g_dur)},"
                    f"Modern,,0,0,0,,{' '.join(chunks)}"
                )
                t += g_dur
            continue
        total_chars = sum(len(w) for w in words) or 1
        chunks = []
        for w in words:
            cs = max(1, int(seg["duration"] * len(w) / total_chars * 100))  # centiseconds
            chunks.append(f"{{\\kf{cs}}}{_escape_ass(w)}")
        text = " ".join(chunks)
        lines.append(
            f"Dialogue: 0,{_ass_time(seg['start'])},{_ass_time(seg['start'] + seg['duration'])},"
            f"Modern,,0,0,0,,{text}"
        )
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def make_music_bed(duration: float, dest: str, sr: int = 44100, level: float = 0.06) -> None:
    """Synthesize a soft ambient pad (Am–F–C–G), written as 16-bit WAV."""
    # Frequencies for Am F C G triads
    chords = [
        [110.0, 130.81, 164.81],   # Am
        [87.31, 110.0, 130.81],    # F
        [130.81, 164.81, 196.0],   # C
        [98.0, 123.47, 146.83],    # G
    ]
    chord_len = 12.0
    n = int(duration * sr)
    t = np.arange(n) / sr
    sig = np.zeros(n)
    pos = 0
    ci = 0
    while pos < n:
        end = min(n, pos + int(chord_len * sr))
        seg_t = np.arange(end - pos) / sr
        chord = np.zeros(end - pos)
        for fq in chords[ci % len(chords)]:
            chord += np.sin(2 * np.pi * fq * seg_t) * 0.33
            chord += np.sin(2 * np.pi * fq * 2 * seg_t) * 0.08
        # slow swell envelope
        env = np.minimum(1, seg_t / 3.0) * np.minimum(1, (len(seg_t) / sr - seg_t + 3.0) / 3.0 + 0.001)
        env = np.clip(env, 0, 1)
        sig[pos:end] += chord * env
        pos = end
        ci += 1
    # global fade in/out
    fade = int(2.5 * sr)
    sig[:fade] *= np.linspace(0, 1, fade)
    sig[-fade:] *= np.linspace(1, 0, fade)
    sig = np.clip(sig * level / max(1e-6, np.abs(sig).max()), -1, 1)
    pcm = (sig * 32767).astype(np.int16)
    with wave.open(dest, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def render_segment(image: str, audio: str, duration: float, dest: str, zoom_in: bool) -> float:
    """Render one Ken Burns segment. Returns the segment's total duration."""
    total = duration + SEG_TAIL
    frames = max(1, int(total * FPS))
    if zoom_in:
        z_expr = f"1+0.12*on/{frames}"
    else:
        z_expr = f"1.12-0.12*on/{frames}"
    vf = (f"scale=2560:1440,"
          f"zoompan=z='{z_expr}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
          f"format=yuv420p")
    _run([
        "ffmpeg", "-y", "-v", "error",
        "-loop", "1", "-framerate", str(FPS), "-i", image,
        "-i", audio,
        "-filter_complex", f"[0:v]{vf}[v]",
        "-map", "[v]", "-map", "1:a",
        "-af", f"apad=whole_dur={total:.2f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        "-t", f"{total:.2f}", "-shortest", dest,
    ])
    return total


def assemble(job_dir: str, segments: list[dict], images: list[str], audios: list[dict],
            output_path: str, progress_cb=None, subtitles: bool = True) -> dict:
    """
    segments: script segments (narration text).
    images:   one image path per segment.
    audios:   [{path, duration}] per segment.
    subtitles: burn karaoke .ass subtitles when True.
    """
    seg_dir = os.path.join(job_dir, "segments")
    os.makedirs(seg_dir, exist_ok=True)

    timed = []
    t = 0.0
    seg_files = []
    n = len(segments)
    for i in range(n):
        dest = os.path.join(seg_dir, f"seg_{i:03d}.mp4")
        dur = render_segment(images[i], audios[i]["path"], audios[i]["duration"],
                             dest, zoom_in=(i % 2 == 0))
        timed.append({"narration": segments[i]["narration"], "start": t, "duration": dur})
        t += dur
        seg_files.append(dest)
        if progress_cb:
            progress_cb(i + 1, n, stage_detail="render")

    # concat
    lst = os.path.join(job_dir, "concat.txt")
    with open(lst, "w") as f:
        for p in seg_files:
            # absolute: the concat demuxer resolves relative paths against
            # the playlist location, which would double the prefix
            f.write(f"file '{os.path.abspath(p)}'\n")
    concat_mp4 = os.path.join(job_dir, "concat.mp4")
    _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
          "-i", lst, "-c", "copy", concat_mp4])

    # subtitles (optional)
    if subtitles:
        ass_path = os.path.join(job_dir, "subs.ass")
        build_subtitles(timed, ass_path)
        vf_sub = f"[0:v]subtitles='{ass_path}'[v]"
    else:
        vf_sub = "[0:v]copy[v]"

    # music bed
    music_wav = os.path.join(job_dir, "music.wav")
    make_music_bed(t, music_wav)

    # final mix (+ burn subtitles when enabled)
    _run([
        "ffmpeg", "-y", "-v", "error",
        "-i", concat_mp4, "-i", music_wav,
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0:weights=1 0.12[a];"
        f"{vf_sub}",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", output_path,
    ])
    if progress_cb:
        progress_cb(n, n, stage_detail="final")
    return {"output": output_path, "duration": t, "segments": n}
