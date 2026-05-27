"""FastAPI entrypoint. Run with: uvicorn app.main:app --reload --port 8765"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .db.session import init_db

app = FastAPI(title="SelfLearningBot", version="0.1.0")

# Permissive CORS for local Electron + Vite dev. Tighten before any deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/")
def root() -> dict:
    return {"name": "SelfLearningBot", "status": "ok"}
