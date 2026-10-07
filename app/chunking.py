"""Turn documents into chunks that carry their source (file name and page)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class Chunk:
    id: str
    file: str
    page: int
    text: str


def load_pages(path: Path) -> list[tuple[int, str]]:
    """Return (page_number, text) pairs. Markdown and text files count as one page."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return [(i + 1, (p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    if suffix in {".md", ".txt"}:
        return [(1, path.read_text(encoding="utf-8"))]
    raise ValueError(f"unsupported file type: {path.name}")


def _normalise(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Split on paragraph boundaries first, then pack paragraphs into chunks of about `size`
    characters. Long paragraphs are cut by sentence. Consecutive chunks overlap by `overlap`
    characters so a fact on a boundary is not lost."""
    paragraphs = [p.strip() for p in _normalise(text).split("\n\n") if p.strip()]
    pieces: list[str] = []
    for p in paragraphs:
        if len(p) <= size:
            pieces.append(p)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", p)
        buf = ""
        for s in sentences:
            if len(buf) + len(s) + 1 > size and buf:
                pieces.append(buf)
                buf = s
            else:
                buf = f"{buf} {s}".strip()
        if buf:
            pieces.append(buf)

    chunks: list[str] = []
    buf = ""
    for piece in pieces:
        if len(buf) + len(piece) + 2 > size and buf:
            chunks.append(buf)
            tail = buf[-overlap:] if overlap else ""
            buf = f"{tail}\n\n{piece}".strip() if tail else piece
        else:
            buf = f"{buf}\n\n{piece}".strip()
    if buf:
        chunks.append(buf)
    return chunks


def chunk_document(path: Path, size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page, text in load_pages(path):
        for n, part in enumerate(split_text(text, size, overlap)):
            chunks.append(Chunk(id=f"{path.name}#p{page}-{n}", file=path.name, page=page, text=part))
    return chunks


def chunk_directory(docs_dir: Path, size: int, overlap: int) -> list[Chunk]:
    files = sorted(p for p in docs_dir.iterdir() if p.suffix.lower() in {".pdf", ".md", ".txt"})
    chunks: list[Chunk] = []
    for f in files:
        chunks.extend(chunk_document(f, size, overlap))
    return chunks
