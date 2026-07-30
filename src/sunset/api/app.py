"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI

from sunset.api.routes import router
from sunset.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sunset",
        description="Assembles the case for deprecating a software feature. "
                    "A human signs the death warrant.",
        version="0.1.0",
    )

    @app.get("/")
    def root() -> dict:
        return {
            "product": "Sunset",
            "positioning": "Sunset assembles the case. A human signs the death warrant.",
            "llm_mode": settings.llm_mode,
            "vector_backend": settings.vector_backend,
            "note": ("Running in offline stub mode — verdicts exercise the full "
                     "pipeline but the accuracy headline is suppressed. Set a Gemini "
                     "key and SUNSET_LLM_MODE=live for a model score."
                     if settings.llm_mode == "offline" else None),
        }

    app.include_router(router)
    return app


app = create_app()
