---
name: iii-doc-ingestion
description: >-
  Use when converting documents (PDF, docx, pptx, xlsx, images, audio, html) to markdown, chunking
  converted text, or ingesting documents for RAG and agent memory. Covers a Python markitdown worker
  exposing doc::convert, doc::chunk, and doc::ingest, plus HTTP-upload and queue triggers and
  chaining into a memory or vector worker.
---

# Document Ingestion

Wrap [microsoft/markitdown](https://github.com/microsoft/markitdown) as an iii worker so agents can
turn arbitrary files into markdown and feed them into a RAG or memory store. markitdown is a Python
library (`pip install markitdown`), so the converter belongs in a Python worker; callers in any SDK
trigger it by function ID.

## Functions

| Function | Payload | Returns |
| --- | --- | --- |
| `doc::convert` | `{ path?, bytes_b64?, mime?, name? }` | `{ markdown, title, name }` |
| `doc::chunk` | `{ markdown, max_chars?, overlap? }` | `{ chunks: [{ index, text }] }` |
| `doc::ingest` | `{ path?/bytes_b64, name, collection }` | `{ doc_id, chunk_count }` |

`doc::ingest` is the composite: it calls `doc::convert`, then `doc::chunk`, then hands chunks to the
memory worker. Keep `convert` and `chunk` separately registered so other pipelines can reuse them.

## Worker Manifest

```yaml
name: markitdown-worker
runtime:
  kind: python
  package_manager: pip
  entry: doc_worker.py
scripts:
  install: "pip install markitdown iii-sdk"
  start: "python doc_worker.py"
```

## Python Worker

```python
import base64, hashlib, tempfile
from markitdown import MarkItDown
from iii import register_worker

iii = register_worker("ws://localhost:49134")
md = MarkItDown()

def _materialize(payload):
    if payload.get("path"):
        return payload["path"]
    raw = base64.b64decode(payload["bytes_b64"])
    suffix = payload.get("name", "upload.bin")
    f = tempfile.NamedTemporaryFile(delete=False, suffix="_" + suffix)
    f.write(raw); f.close()
    return f.name

def convert(payload):
    src = _materialize(payload)
    result = md.convert(src)  # PDF, docx, pptx, xlsx, images, audio, html, ...
    return {
        "markdown": result.text_content,
        "title": result.title or payload.get("name"),
        "name": payload.get("name"),
    }

def chunk(payload):
    text = payload["markdown"]
    size = payload.get("max_chars", 1200)
    overlap = payload.get("overlap", 150)
    step = max(1, size - overlap)
    chunks = [
        {"index": i // step, "text": text[i:i + size]}
        for i in range(0, len(text), step)
    ]
    return {"chunks": chunks}

def ingest(payload):
    doc = iii.trigger({"function_id": "doc::convert", "payload": payload})
    parts = iii.trigger({
        "function_id": "doc::chunk",
        "payload": {"markdown": doc["markdown"]},
    })["chunks"]
    doc_id = hashlib.sha1(doc["markdown"].encode()).hexdigest()[:16]
    for part in parts:
        iii.trigger({
            "function_id": "memory::upsert",
            "payload": {
                "collection": payload["collection"],
                "id": f"{doc_id}:{part['index']}",
                "text": part["text"],
                "metadata": {"doc_id": doc_id, "name": doc["name"]},
            },
        })
    return {"doc_id": doc_id, "chunk_count": len(parts)}

iii.register_function("doc::convert", convert)
iii.register_function("doc::chunk", chunk)
iii.register_function("doc::ingest", ingest)
```

`memory::upsert` is the embed-and-store function exposed by a memory or vector worker installed from
`workers.iii.dev` (`iii worker add memory`). The doc worker stays storage-agnostic; swap the target
function ID to target a different store.

## Trigger From an HTTP Upload

Bind an HTTP trigger so an upload endpoint converts and ingests in one request. The handler payload
carries `body`; base64-encode binary uploads client-side, or have a gateway worker do it.

```python
iii.register_trigger({
    "type": "http",
    "function_id": "doc::ingest",
    "config": {"api_path": "/docs/ingest", "http_method": "POST"},
})
```

The POST body maps to the `doc::ingest` payload: `{ bytes_b64, name, collection }`.

## Trigger From a Queue (Batch)

For bulk backfills, enqueue one message per file and let a durable subscriber drain it. The enqueue
invocation mode gives retries and queue policy, so a single malformed file does not lose the batch.

```python
iii.register_trigger({
    "type": "durable:subscriber",
    "function_id": "doc::ingest",
    "config": {"topic": "doc-ingest"},
})
```

## TypeScript Caller

A producer in any SDK enqueues files for batch conversion, or calls `doc::convert` synchronously when
it needs the markdown back immediately.

```typescript
import { registerWorker, TriggerAction } from "iii-sdk";

const iii = registerWorker("ws://localhost:49134", { workerName: "doc-producer" });

// Synchronous one-off: get markdown back to the caller.
const { markdown } = await iii.trigger({
  function_id: "doc::convert",
  payload: { bytes_b64: fileB64, name: "spec.pdf" },
});

// Batch: enqueue each file for reliable async ingestion.
for (const file of files) {
  await iii.trigger({
    function_id: "doc::ingest",
    payload: { bytes_b64: file.b64, name: file.name, collection: "handbook" },
    action: TriggerAction.Enqueue({ queue: "doc-ingest" }),
  });
}
```

## Notes

- Pass file bytes as base64 in the payload, or a shared `path` when the worker and caller see the
  same filesystem. For large files prefer a channel (`createChannel()`) over inlining bytes in JSON.
- Image and audio conversion in markitdown can call out to an LLM or transcription model; supply
  those credentials via environment variables in the worker process, never in payloads or metadata.
- Keep `doc::convert` pure (file in, markdown out) so it is reusable; put storage side effects only
  in `doc::ingest`.
- Use sync invocation when the caller needs the markdown, enqueue for reliable batch ingestion, and
  void only for fire-and-forget reindex signals.
