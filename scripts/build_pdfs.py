"""Render the sample documents in data/docs-src/*.md to PDFs in data/docs/.

Each level-2 section starts a new page, so citations point to a specific page like a real
company document would. Uses headless Chrome, which is on most machines; no PDF library needed.

    uv run python scripts/build_pdfs.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "docs-src"
OUT = ROOT / "data" / "docs"

CSS = """
@page { size: A4; margin: 22mm 20mm 24mm 20mm; }
body { font-family: "Liberation Sans", Arial, sans-serif; font-size: 11.5pt; line-height: 1.5; color: #1b2a33; }
.letterhead { display: flex; justify-content: space-between; align-items: baseline;
  border-bottom: 2px solid #0E2B38; padding-bottom: 6pt; margin-bottom: 18pt; }
.letterhead b { font-size: 15pt; color: #0E2B38; }
.letterhead span { font-size: 9pt; color: #5B6B72; }
h1 { font-size: 20pt; margin: 0 0 6pt; color: #0E2B38; }
h2 { font-size: 13.5pt; margin: 0 0 8pt; color: #0E2B38; border-left: 4px solid #7FE3D2; padding-left: 8pt; }
h2:not(:first-of-type) { page-break-before: always; }
p { margin: 0 0 9pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 12pt; font-size: 10.5pt; }
th, td { border-bottom: 1px solid #D7DEDA; padding: 5pt 6pt; text-align: left; vertical-align: top; }
th { background: #F1F3F0; }
.disclaimer { margin-top: 24pt; font-size: 8.5pt; color: #5B6B72; border-top: 1px solid #D7DEDA; padding-top: 6pt; }
"""

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>
<body>
<div class="letterhead"><b>Nordlicht Haustechnik GmbH</b><span>{doc_name} · version 2026-01</span></div>
{body}
<p class="disclaimer">Nordlicht Haustechnik GmbH is a fictional company. This document exists to demonstrate a document-based support assistant.</p>
</body></html>"""


def chrome() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if shutil.which(name):
            return name
    sys.exit("no Chrome/Chromium found on PATH")


def build(md_path: Path) -> Path:
    html_body = markdown.markdown(md_path.read_text("utf-8"), extensions=["tables"])
    doc_name = md_path.stem.replace("-", " ")
    html = TEMPLATE.format(css=CSS, body=html_body, doc_name=doc_name)
    out = OUT / (md_path.stem + ".pdf")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        tmp = Path(f.name)
    try:
        subprocess.run(
            [chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={out}", tmp.as_uri()],
            check=True, capture_output=True, timeout=60,
        )
    finally:
        tmp.unlink(missing_ok=True)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for md in sorted(SRC.glob("*.md")):
        out = build(md)
        print(f"{md.name} -> {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
