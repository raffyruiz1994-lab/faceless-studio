# fal.ai provider — wiring checklist (DRAFT)

Only do this after Rafael confirms his "faia" API is fal.ai.

## Code
1. `app/settings_store.py` — add to `_DEFAULTS`:
   - `image_provider`: `"gemini"` (allowed values: `gemini`, `falai`)
   - `fal_api_key`: `""`
   - Expose `fal_api_key_set` + `image_provider` in `get_public_settings()`.
2. `app/pipeline.py` (images step) — dispatch:
   ```python
   provider = spec.get("image_provider") or settings.get("image_provider", "gemini")
   if provider == "falai":
       from .providers import falai as images_mod
       img_key = settings["fal_api_key"]
       img_model = spec.get("image_model") or settings.get("fal_image_model", "fal-ai/flux/dev")
   else:
       img_key = settings["gemini_api_key"]
       ...
   ```
   Keep `style` / `progress_cb` as-is — the falai module honors both.
3. Dashboard `static/index.html` (Ajustes): add "Proveedor de imágenes"
   selector (Nano Banana 2 directo / fal.ai) + "API key de fal.ai" field.
   (Nuevo video): optional per-job provider override.
4. `README_DEPLOY.md`: note that fal.ai bills via prepaid credits per its current
   terms (pay-as-you-go per image, no subscription) and where to get the key
   (fal.ai dashboard → API keys).
5. Commit + push to `main` on Rafael's repo (he must re-pull on his VM).

## Test before pushing
- `python -c "from app.providers import falai"` (syntax/import OK)
- Real generation smoke test needs a valid FAL_KEY; one image via the
  dashboard on a demo job is enough.
- Watch the first run: fal.ai queue responses include `queue_position`;
  long queues at peak hours may hit the 10-min per-image timeout.

## If "faia" turns out to be another provider
- Freepik / Firefly / Replicate: same pattern — new file in
  `app/providers/`, same function signature, swap step 2.
