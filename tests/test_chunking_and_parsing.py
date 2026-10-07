from pathlib import Path

from app.chunking import chunk_document, split_text
from app.llm import parse_answer


def test_split_respects_size_and_keeps_text():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 40 for i in range(12))
    chunks = split_text(text, size=600, overlap=100)
    assert len(chunks) > 1
    assert all(len(c) <= 600 + 100 + 60 for c in chunks)
    assert "Paragraph 0." in chunks[0]
    assert "Paragraph 11." in chunks[-1]


def test_chunk_document_carries_file_and_page(tmp_path: Path):
    f = tmp_path / "terms.md"
    f.write_text("# Terms\n\nSaturday service runs 8:00 to 16:00.\n\nSunday closed.", "utf-8")
    chunks = chunk_document(f, size=900, overlap=100)
    assert len(chunks) == 1
    assert chunks[0].file == "terms.md"
    assert chunks[0].page == 1
    assert "16:00" in chunks[0].text


def test_parse_answer_accepts_fenced_json():
    raw = 'Sure:\n```json\n{"answer": "Yes, Saturdays.", "sources": [{"file": "a.pdf", "page": 2}], "handover": false, "reason": ""}\n```'
    parsed = parse_answer(raw)
    assert parsed is not None
    assert parsed.answer == "Yes, Saturdays."
    assert parsed.sources[0].page == 2
    assert parsed.handover is False


def test_parse_answer_rejects_garbage():
    assert parse_answer("I don't know") is None
    assert parse_answer('{"answer": 5}') is None
