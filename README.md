# 🎬 Fosil Studio

Centro de control para crear videos faceless estilo **Fósil Mental** (doodle de
tinta + pintura digital, una ilustración por idea narrada, subtítulos quemados
y rótulos marcador): el programa escribe el guion por escenas → genera
ilustraciones (o clips animados con Veo/Kling) → sintetiza la narración en
español → quema subtítulos y **edita el video final solo**.

Incluye además el motor clásico (documentales cinematográficos con
subtítulos karaoke).

## Uso rápido

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# abre http://localhost:8000  (solo tu red local)
```

1. **Ajustes**: pega tus keys — Google AI Studio (guion + imágenes + Veo),
   fal.ai (imágenes FLUX + clips Kling) y Fish Audio (narración).
2. **Nuevo video**: tema, duración promedio, diseño, clips animados,
   subtítulos on/off → Crear video.
3. **Ideas IA**: feed conectado a la IA que trae ideas de videos por nicho.
4. **Probar sin APIs**: demo local del motor Fosil (sin gastar nada).
5. Cuando el trabajo termina: previsualiza, descarga el MP4 y completa el
   `REVIEW_CHECKLIST.md` del trabajo **antes** de subirlo a YouTube.

## Estructura

```
app/
  main.py           # FastAPI: /api/jobs, /api/settings, sirve el frontend
  pipeline.py       # orquestador clásico + run_fosil_job (motor Fosil)
  fosil.py          # guion por escenas estilo Fósil Mental + clips Veo/fal.ai
  fosil_assemble.py # ffmpeg: clip o Ken Burns + subtítulos .srt + rótulos
  script_gen.py     # etapa 1 (clásico): guion JSON vía Gemini
  images.py         # etapa 2: Nano Banana 2 (+ estilo doodle "fosil")
  providers/falai.py# imágenes FLUX vía fal.ai (queue API)
  voice.py          # etapa 3: Fish Audio TTS por segmento
  assemble.py       # etapa 4 (clásico): Ken Burns + subtítulos .ass karaoke
  demo.py           # modo demo sin APIs (clásico y fosil)
  settings_store.py # settings.json (0600), las keys nunca se exponen
static/index.html   # dashboard Fosil Studio (sin build step)
jobs/<id>/          # script.json, images/, voice/, output.mp4, REVIEW_CHECKLIST.md
```

## Motores

| Motor | Guion | Visuales | Subtítulos |
|---|---|---|---|
| **fosil** (default) | escenas con rótulo (gancho→bloques→cierre) | ilustraciones doodle o clips Veo/Kling | .srt estilo canal |
| classic | segmentos 60-110 palabras | Nano Banana cinematográfico/stick | .ass karaoke |

## APIs necesarias

| Para | API | Costo aprox. |
|---|---|---|
| Guion + ideas | Google AI Studio (Gemini) | ~$0.01/video |
| Ilustraciones | Nano Banana (Google) o FLUX (fal.ai) | ~$0.04/imagen |
| Clips animados (opcional) | Veo 3.1 Fast (Google) o Kling (fal.ai) | ~$0.10/seg y ~$0.084/seg |
| Narración español | Fish Audio | ~$15/1M bytes |
| Edición | ffmpeg local | $0 |

Video estilo Fósil de ~3 min: **~$0.30** solo ilustraciones · **~$6.50** con clips.

## Despliegue en tu VM
Ver [README_DEPLOY.md](README_DEPLOY.md) (Docker Compose o systemd).

## Notas honestas
- El modelo **no inventa bibliografía**: lo que no puede verificar va a
  `review_flags` y al checklist. La revisión humana antes de publicar no es
  opcional: YouTube desmonetiza canales "fábrica" sin revisión editorial
  (política de *inauthentic content*).
- Costo típico video 16 min: ~$2.10 (28 imgs × $0.067 + voz).
