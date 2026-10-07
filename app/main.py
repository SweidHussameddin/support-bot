"""HTTP layer. Three endpoints and the static widget.

    uv run uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.chat import ChatReply, ChatService
from app.config import settings
from app.index import Index
from app.llm import ModelUnavailable

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("support-bot")

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not (settings.index_dir / "chunks.json").exists():
        raise RuntimeError("no index found, run `uv run support-bot-ingest` first")
    index = Index.load(settings.index_dir)
    app.state.chat = ChatService(index)
    log.info("index loaded: %d chunks, models %s", len(index.chunks), settings.models)
    yield


app = FastAPI(title=settings.app_title, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


class HumanRequest(BaseModel):
    session_id: str


@app.get("/")
def demo_site() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "models": settings.models, "chunks": len(app.state.chat.index.chunks)}


@app.post("/api/chat", response_model=ChatReply)
def chat(req: ChatRequest) -> ChatReply:
    session_id = req.session_id or uuid.uuid4().hex
    try:
        return app.state.chat.reply(session_id, req.message.strip())
    except ModelUnavailable as e:
        log.error("model unavailable: %s", e)
        raise HTTPException(
            status_code=503,
            detail="The assistant is temporarily unavailable. Please try again in a minute.",
        ) from e
    except RuntimeError as e:  # missing key etc.
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/api/handover")
def handover(req: HumanRequest) -> dict:
    app.state.chat.request_human(req.session_id)
    return {"ok": True}
