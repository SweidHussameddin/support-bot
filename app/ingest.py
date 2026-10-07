"""Build the search index from everything in data/docs. Run again whenever documents change:

    uv run support-bot-ingest
"""

from __future__ import annotations

import sys
import time

from app.chunking import chunk_directory
from app.config import settings
from app.index import Index


def main() -> int:
    docs = settings.docs_dir
    if not docs.exists():
        print(f"no documents directory: {docs}", file=sys.stderr)
        return 1
    t0 = time.time()
    chunks = chunk_directory(docs, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        print(f"no .pdf, .md or .txt files in {docs}", file=sys.stderr)
        return 1
    files = sorted({c.file for c in chunks})
    print(f"{len(files)} files, {len(chunks)} chunks, embedding with {settings.embedding_model} ...")
    index = Index.build(chunks, settings.embedding_model)
    index.save(settings.index_dir)
    print(f"index written to {settings.index_dir} in {time.time() - t0:.1f}s")
    for f in files:
        n = sum(1 for c in chunks if c.file == f)
        print(f"  {f}: {n} chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
