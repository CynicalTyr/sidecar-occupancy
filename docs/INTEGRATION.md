# Integration patterns

This kernel is the **client policy** for a single-flight HTTP sidecar.
The sidecar itself lives elsewhere (Curiosity-Docker or your own lock).

```
MCP host
    │
    ▼
examples/mcp_server.py   → occupancy_classify / occupancy_should_abort
    │                         (no retry / hammer tool)
    ▼
Your scan worker (HTTP)  → GET /health  POST /scan
```

Do **not** wrap `/scan` in Tenacity `@retry` or urllib3
`Retry(status_forcelist={503})`. Those retry the *same call*. Occupancy
needs the **outer** handle loop to `break`.

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

## Timeouts (do not invert)

Keep **client wait longer than worker scan cap**. Curiosity-Docker’s
documented pair is client **120s** vs scan **60s** (env **names**
`USERNAME_DISCOVERY_TIMEOUT` / `USERNAME_DISCOVERY_SCAN_TIMEOUT`). If the
client is shorter, a slow-but-finishing scan becomes fake `timeout`, and
the next POST is 503 because the lock is still held.

## Curiosity-Docker

Install and health-check the sidecar using that repo’s START_HERE. Then
wrap `/scan`:

- Client timeout **120s**, container scan timeout **60s**.
- On 503: `should_break_handle_loop("busy")` → end batch.
- Empty `hits: []` is a **completed** scan. Stamp “looked,” not a 72h
  penalty for a chatty LLM.

HTTP kinds table: [Curiosity-Docker `docs/HTTP_API.md`](https://github.com/CynicalTyr/Curiosity-Docker/blob/main/docs/HTTP_API.md).

## HTTP client (local agent)

```python
from occupancy import abort_sweep, classify_http, should_break_handle_loop

consecutive_hard = 0
for handle in handles:
    status, timed_out, transport_error = post_scan(handle)  # your HTTP
    kind = classify_http(status, timed_out=timed_out, transport_error=transport_error)
    if should_break_handle_loop(kind):
        consecutive_hard += 1
        if abort_sweep(consecutive_hard):
            break  # abandon the sweep this cycle
        break      # occupancy: resume remaining handles next cycle
    consecutive_hard = 0
    # ok / empty / http_error: your cooldown / ledger logic
```

Disable library retries on occupancy:

- Tenacity (`libraryId=/jd/tenacity`): do not decorate `post_scan` with
  `retry_if_exception_type` / `retry_if_result` for 503.
- urllib3 (`libraryId=/urllib3/urllib3`): leave 503 **out** of
  `status_forcelist`. `RETRY_AFTER_STATUS_CODES` already includes 503
  when a Retry-After header is present — do not also force-retry it.
- Resilience4j `RetryConfig`: do not treat occupancy as
  `retryOnResult` / `retryExceptions` for the scan supplier.

## MCP (harness)

```bash
python3 -m pip install -r examples/requirements-mcp.txt
```

Absolute path to `examples/mcp_server.py`. Logs on stderr only.
Tools: `occupancy_classify`, `occupancy_should_abort`. There is **no**
hammer-retry tool. See [`MCP.md`](MCP.md).

## Paste-ready policy

> One scan at a time. On busy/timeout/transport, stop the batch. Do not
> retry 503 in a tight loop. Client timeout must stay longer than the
> worker timeout. Hits are unverified URLs. Empty hits still count toward
> the cycle cap.
