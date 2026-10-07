"""Local search index: dense embeddings (fastembed, CPU, no external service) plus BM25 keyword
search, merged with reciprocal rank fusion. Numbers, article codes and prices are matched by
BM25; paraphrased questions by the embeddings."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from app.chunking import Chunk

_TOKEN = re.compile(r"[a-z0-9äöüß]+(?:[.,][0-9]+)*")
_STOP = frozenset(
    ["a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "for", "by", "with", "from", "is", "are", "was", "were", "be", "do", "does", "did", "you", "your", "we", "our", "us", "i", "my", "it", "its", "this", "that", "these", "those", "can", "could", "would", "should", "will", "there", "here", "what", "when", "where", "which", "who", "how", "much", "many", "any", "some", "also", "not", "no", "yes", "please", "ich", "wir", "sie", "ihr", "du", "der", "die", "das", "ein", "eine", "und", "oder", "von", "zu", "in", "auf", "für", "mit", "ist", "sind", "habt", "haben", "kann", "wann", "wo", "wie", "was"]
)


def _stem(tok: str) -> str:
    """Very light English stemming so 'weekends' matches 'weekend' and 'pumps' matches 'pump'."""
    if len(tok) > 4 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 4 and tok.endswith("es") and tok[-3] in "sxz":
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class SearchHit:
    __slots__ = ("chunk", "score")

    def __init__(self, chunk: Chunk, score: float) -> None:
        self.chunk = chunk
        self.score = score


class Index:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray, model_name: str) -> None:
        self.chunks = chunks
        self.vectors = vectors  # L2-normalised, shape (n, dim)
        self.model_name = model_name
        self._bm25 = BM25Okapi([tokenize(c.text) for c in chunks]) if chunks else None
        self._embedder = None

    # ---- persistence -------------------------------------------------------------------
    def save(self, index_dir: Path) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        np.save(index_dir / "vectors.npy", self.vectors)
        meta = {"model": self.model_name, "chunks": [asdict(c) for c in self.chunks]}
        (index_dir / "chunks.json").write_text(json.dumps(meta, ensure_ascii=False), "utf-8")

    @classmethod
    def load(cls, index_dir: Path) -> Index:
        meta = json.loads((index_dir / "chunks.json").read_text("utf-8"))
        chunks = [Chunk(**c) for c in meta["chunks"]]
        vectors = np.load(index_dir / "vectors.npy")
        return cls(chunks, vectors, meta["model"])

    @classmethod
    def build(cls, chunks: list[Chunk], model_name: str) -> Index:
        vectors = embed([c.text for c in chunks], model_name)
        return cls(chunks, vectors, model_name)

    # ---- search ------------------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        if not self.chunks:
            return []
        q = embed([query], self.model_name)[0]
        dense = self.vectors @ q
        dense_rank = np.argsort(-dense)
        bm25 = self._bm25.get_scores(tokenize(query))
        bm25_rank = np.argsort(-bm25)

        # weighted reciprocal rank fusion; k=60 is the usual constant. Dense gets more weight:
        # it understands paraphrases, BM25 is there to pin exact numbers and codes.
        fused: dict[int, float] = {}
        for rank, i in enumerate(dense_rank[: top_k * 3]):
            fused[int(i)] = fused.get(int(i), 0.0) + 1.2 / (60 + rank)
        for rank, i in enumerate(bm25_rank[: top_k * 3]):
            if bm25[i] > 0:
                fused[int(i)] = fused.get(int(i), 0.0) + 0.8 / (60 + rank)
        best = sorted(fused.items(), key=lambda kv: -kv[1])[:top_k]
        return [SearchHit(self.chunks[i], s) for i, s in best]


_models: dict[str, object] = {}


def embed(texts: list[str], model_name: str) -> np.ndarray:
    """Embed texts with fastembed (ONNX on CPU). The model is downloaded once and cached."""
    from fastembed import TextEmbedding

    model = _models.get(model_name)
    if model is None:
        model = _models[model_name] = TextEmbedding(model_name=model_name)
    vecs = np.array(list(model.embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.maximum(norms, 1e-9)
