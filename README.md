# 🎬 Faceless Studio

Genera documentales faceless cinematográficos (estilo "toda la historia de X en
16 minutos"): guion con tesis narrativa → imágenes cinematográficas con
Nano Banana 2 → narración con Fish Audio → ensamblaje local con efecto
Ken Burns, subtítulos modernos karaoke y música ambiental.

## Uso rápido

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# abre http://localhost:8000
```

1. **Ajustes**: pega tu Gemini API Key y tu Fish Audio API Key (+ Voice ID opcional).
2. **Nuevo video**: tema, idioma, minutos → Generar video.
3. **Probar sin APIs**: corre la demo local (imágenes de prueba + audio silencioso)
   para verificar que el pipeline funciona en tu máquina sin gastar nada.
4. Cuando el trabajo termina: previsualiza, descarga el MP4 y completa el
   `REVIEW_CHECKLIST.md` del trabajo **antes** de subirlo a YouTube.

## Estructura

```
app/
  main.py           # FastAPI: /api/jobs, /api/settings, sirve el frontend
  pipeline.py       # orquestador de las 4 etapas + checklist de revisión
  script_gen.py     # etapa 1: guion JSON vía Gemini (con review_flags honestos)
  images.py         # etapa 2: Nano Banana 2, una imagen 16:9 por segmento
  voice.py          # etapa 3: Fish Audio TTS por segmento
  assemble.py       # etapa 4: ffmpeg Ken Burns + subtítulos .ass karaoke + música
  demo.py           # modo demo sin APIs
  settings_store.py # settings.json (0600), las keys nunca se exponen
static/index.html   # frontend (sin build step)
jobs/<id>/          # script.json, images/, voice/, output.mp4, REVIEW_CHECKLIST.md
```

## Despliegue en tu VM
Ver [README_DEPLOY.md](README_DEPLOY.md) (Docker Compose o systemd).

## Notas honestas
- El modelo **no inventa bibliografía**: lo que no puede verificar va a
  `review_flags` y al checklist. La revisión humana antes de publicar no es
  opcional: YouTube desmonetiza canales "fábrica" sin revisión editorial
  (política de *inauthentic content*).
- Costo típico video 16 min: ~$2.10 (28 imgs × $0.067 + voz).
