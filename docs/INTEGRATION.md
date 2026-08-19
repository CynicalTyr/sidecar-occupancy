# Integration patterns

This kernel is the **client policy** for a single-flight HTTP sidecar.
The sidecar itself lives elsewhere (Curiosity-Docker or your own lock).

```
MCP host
    │
    ▼
examples/mcp_server.py   → occupancy_classify / occupancy_should_abort
    │
    ▼
Your scan worker (HTTP)  → Curiosity-Docker GET /health POST /scan
```

## Map HTTP to kinds

| HTTP / client | `classify_http` |
| ------------- | ---------------- |
| 200 with body | `ok` (you may still treat empty hits as `empty` in *your* wrapper) |
| 503 | `busy` |
| client timeout | `timed_out=True` → `timeout` |
| connection error | `transport_error=True` → `transport` |
| other 4xx/5xx | `http_error` |

`http_error` does **not** break the handle loop by default (might be one
bad handle). `busy` / `timeout` / `transport` **do**.

## Curiosity-Docker

Install and health-check the sidecar using that repo’s START_HERE. Then
wrap `/scan`:

- Client timeout **120s**, container scan timeout **60s**.
- On 503: `should_break_handle_loop("busy")` → end batch.
- Empty `hits: []` is a **completed** scan. Stamp “looked,” not a 72h
  penalty for a chatty LLM.

## MCP

```bash
python3 -m pip install -r examples/requirements-mcp.txt
```

Absolute path to `examples/mcp_server.py`. Logs on stderr only.

## Paste-ready policy

> One scan at a time. On busy/timeout/transport, stop the batch. Hits are
> unverified URLs. Empty hits still count toward the cycle cap.
