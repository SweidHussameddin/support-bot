"""Conversation orchestration: retrieve, ask the model, decide on handover, remember the turn."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from datetime import UTC, datetime

import httpx
from pydantic import BaseModel

from app import llm
from app.config import settings
from app.index import Index

log = logging.getLogger("support-bot.chat")


class SourceOut(BaseModel):
    file: str
    page: int


class ChatReply(BaseModel):
    answer: str
    sources: list[SourceOut]
    handover: bool
    session_id: str


class Sessions:
    """In-memory conversation memory. Good enough for a demo; swap for Redis in production."""

    def __init__(self, turns: int) -> None:
        self._turns = turns
        self._data: dict[str, deque[dict[str, str]]] = {}
        self._lock = threading.Lock()

    def history(self, session_id: str) -> list[dict[str, str]]:
        with self._lock:
            return list(self._data.get(session_id, ()))

    def append(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            q = self._data.setdefault(session_id, deque(maxlen=self._turns * 2))
            q.append({"role": role, "content": content})


class Handover:
    """Writes the full conversation to a JSONL inbox and, if configured, to a webhook."""

    def __init__(self, inbox_path, webhook_url: str) -> None:
        self._path = inbox_path
        self._url = webhook_url

    def send(self, session_id: str, reason: str, history: list[dict[str, str]]) -> None:
        record = {
            "time": datetime.now(UTC).isoformat(timespec="seconds"),
            "session_id": session_id,
            "reason": reason,
            "conversation": history,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        if self._url:
            try:
                httpx.post(self._url, json=record, timeout=5)
            except httpx.HTTPError as e:
                log.warning("handover webhook failed: %s", e)


class ChatService:
    def __init__(self, index: Index) -> None:
        self.index = index
        self.sessions = Sessions(settings.history_turns)
        self.handover = Handover(settings.inbox_file, settings.handover_webhook_url)

    def reply(self, session_id: str, message: str) -> ChatReply:
        t0 = time.time()
        history = self.sessions.history(session_id)
        hits = self.index.search(message, settings.top_k)
        hits = [h for h in hits if h.score >= settings.min_score]

        answer, usage = llm.ask(message, hits, history)

        # Only sources that were actually retrieved may be cited.
        allowed = {(h.chunk.file, h.chunk.page) for h in hits}
        sources: list[SourceOut] = []
        for s in answer.sources:
            key = (s.file, s.page)
            if key in allowed and key not in {(x.file, x.page) for x in sources}:
                sources.append(SourceOut(file=s.file, page=s.page))

        # No passages at all means the documents do not cover the topic: always hand over.
        handover = answer.handover or not hits

        self.sessions.append(session_id, "user", message)
        self.sessions.append(session_id, "assistant", answer.answer)
        if handover:
            self.handover.send(session_id, answer.reason or "model requested handover",
                               self.sessions.history(session_id))

        log.info(
            "session=%s hits=%d handover=%s tokens=%s/%s %.1fs",
            session_id[:8], len(hits), handover,
            usage.get("prompt_tokens", "?"), usage.get("completion_tokens", "?"), time.time() - t0,
        )
        return ChatReply(answer=answer.answer, sources=sources, handover=handover, session_id=session_id)

    def request_human(self, session_id: str) -> None:
        self.sessions.append(session_id, "user", "[customer asked for a person]")
        self.handover.send(session_id, "customer requested a person", self.sessions.history(session_id))
