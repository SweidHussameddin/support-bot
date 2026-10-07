# support-bot

A support chatbot that answers customer questions from your own documents, shows the source it used, and hands the conversation to a person instead of guessing.

Built as a small, readable Python service: one FastAPI process, local retrieval (no vector database to operate), any OpenAI-compatible model via OpenRouter, and a drop-in chat widget for any website.

```
documents (PDF, Markdown)  ──ingest──▶  local index (embeddings + BM25)
                                               │
  website widget  ──POST /api/chat──▶  retrieve top passages ──▶ model (JSON answer + sources + handover flag)
                                               │
                                     handover ──▶ inbox file and/or webhook (n8n, ticket system)
```

## What it does

- **Answers only from your documents.** The model sees the retrieved passages and nothing else. Prices, times and conditions come out exactly as written.
- **Cites its sources.** Every answer carries file name and page. Sources the model did not actually receive are dropped, so it cannot cite something it never saw.
- **Hands over instead of guessing.** Appointment requests, complaints, account questions or anything the documents do not cover produce a friendly handover message, the full conversation is written to an inbox and optionally posted to a webhook.
- **Costs you nothing to run locally.** Embeddings run on the CPU with a small ONNX model. The demo uses a free OpenRouter model; for production you point the same code at any paid model with your own key.

## Run it

Requirements: Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env            # add your OpenRouter API key
uv venv -p 3.12 && uv pip install -e ".[dev]"
uv run support-bot-ingest        # builds data/index from data/docs (first run downloads the embedding model, ~130 MB)
uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 for the demo website with the widget in the corner. The API:

```bash
curl -s localhost:8000/api/chat -H 'content-type: application/json' \
  -d '{"message": "Do you repair heat pumps on weekends?"}'
# {"answer":"Yes. Saturdays 8:00 to 16:00 at the standard rate plus a 25 % surcharge.",
#  "sources":[{"file":"service-conditions.md","page":1}],"handover":false,"session_id":"..."}
```

Send `session_id` back with the next message to keep the conversation context.

## Put the widget on your site

```html
<script src="https://your-host/static/widget.js" data-endpoint="https://your-host" data-title="Support"></script>
```

No framework, no build step, styles are scoped. The widget shows the answer, the sources, a visible handover notice, and a "Talk to a person" button that triggers a handover at any time.

## Your documents

Drop PDFs, Markdown or text files into `data/docs/` and run the ingest again. Page numbers come from the PDF; Markdown files count as one page. The sample documents describe a fictional heating company and exist only for the demo.

## Configuration

Everything is in `.env`, see `.env.example`. The important ones:

| Variable | Meaning |
|---|---|
| `OPENROUTER_API_KEY` | Your key. Never committed, never logged. |
| `OPENROUTER_MODEL` | Any OpenRouter model id. Free ones end in `:free`. |
| `HANDOVER_WEBHOOK_URL` | Where handovers are POSTed as JSON. Empty means file inbox only. |
| `COMPANY_NAME` | Used in the prompt and the widget header. |

## Cost per answer

Each answer sends the system prompt, the retrieved passages and the recent turns to the model, typically 1,200 to 2,000 input tokens and under 150 output tokens. The server logs token counts per request. With a mid-range hosted model that is a fraction of a cent per answer; with a free OpenRouter model it is zero, with rate limits.

## Tests

```bash
uv run pytest
```

The tests cover chunking, JSON parsing of model replies, source filtering, handover rules and session memory. The model call is stubbed, so they run without a key or network.

## Production notes

- Session memory is in-process. Put Redis behind `Sessions` for more than one worker.
- Retrieval is in-memory numpy; fine up to a few thousand pages. Beyond that, swap `Index` for pgvector or Qdrant, the interface stays.
- Put the API behind your reverse proxy and restrict CORS to your domain.
