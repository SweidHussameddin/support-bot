"""End-to-end flow with the model call stubbed out. No network, no API key needed."""

import numpy as np

from app import chat as chat_module
from app.chunking import Chunk
from app.index import Index
from app.llm import ModelAnswer, Source


class FakeIndex(Index):
    def __init__(self, chunks):
        super().__init__(chunks, np.zeros((len(chunks), 4), dtype=np.float32), "fake")

    def search(self, query, top_k=5):
        from app.index import SearchHit
        words = [w.strip("?.,!") for w in query.lower().split()]
        return [SearchHit(c, 0.05) for c in self.chunks if any(w and w in c.text.lower() for w in words)]


def make_service(tmp_path, monkeypatch, answer: ModelAnswer):
    chunks = [Chunk(id="t#p2-0", file="terms.pdf", page=2, text="Saturday emergency service 8:00 to 16:00 plus 25 % surcharge.")]
    monkeypatch.setattr(chat_module.llm, "ask", lambda q, hits, history: (answer, {"prompt_tokens": 10, "completion_tokens": 5}))
    monkeypatch.setattr(chat_module.settings, "inbox_file", tmp_path / "inbox.jsonl")
    monkeypatch.setattr(chat_module.settings, "handover_webhook_url", "")
    return chat_module.ChatService(FakeIndex(chunks))


def test_answer_with_source(tmp_path, monkeypatch):
    svc = make_service(tmp_path, monkeypatch, ModelAnswer(answer="Yes, Saturdays 8 to 16.", sources=[Source(file="terms.pdf", page=2)], handover=False))
    r = svc.reply("s1", "Do you work on saturday?")
    assert r.handover is False
    assert [s.page for s in r.sources] == [2]
    assert not (tmp_path / "inbox.jsonl").exists()


def test_source_not_in_retrieved_passages_is_dropped(tmp_path, monkeypatch):
    svc = make_service(tmp_path, monkeypatch, ModelAnswer(answer="x", sources=[Source(file="made-up.pdf", page=9)], handover=False))
    r = svc.reply("s2", "saturday?")
    assert r.sources == []


def test_no_hits_forces_handover_and_writes_inbox(tmp_path, monkeypatch):
    svc = make_service(tmp_path, monkeypatch, ModelAnswer(answer="Passed to the team.", handover=False))
    r = svc.reply("s3", "zzz")  # nothing matches
    assert r.handover is True
    lines = (tmp_path / "inbox.jsonl").read_text().splitlines()
    assert len(lines) == 1
    assert "zzz" in lines[0]


def test_history_is_kept_per_session(tmp_path, monkeypatch):
    svc = make_service(tmp_path, monkeypatch, ModelAnswer(answer="ok", handover=False))
    svc.reply("s4", "saturday")
    svc.reply("s4", "saturday again")
    assert len(svc.sessions.history("s4")) == 4
    assert svc.sessions.history("other") == []
