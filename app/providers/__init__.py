"""Image-generation providers for Faceless Studio.

DRAFT (uncommitted): pending Rafael confirming that his 'faia' API is fal.ai.
Each provider module exposes the same signature as app/images.py:

    generate_images(script, out_dir, api_key, image_model=..., style=...,
                    progress_cb=None) -> list[str]

so app/pipeline.py can dispatch between providers without changing the rest
of the pipeline.
"""
