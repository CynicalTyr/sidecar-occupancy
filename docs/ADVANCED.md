# Advanced: occupancy vs retries in agent OSINT loops

This guide is for people who already ran [`START_HERE.md`](../START_HERE.md)
and want the design that keeps showing up in production: **why HTTP 503
busy is a lock**, how Tenacity/urllib3 Retry turn that lock into a hang,
and how this kernel differs from retry libraries and from the sidecar
docs they already read.

Search terms this document is meant to answer: *HTTP 503 busy sidecar
agent*, *username discovery livelock*, *Curiosity-Docker occupancy*,
*client timeout longer than scan timeout*, *do not continue on 503*.

---

## 1. The failure that looks like success

A curiosity worker walks a list of handles. The sidecar is single-flight:
one scan holds a mutex. The second POST returns HTTP **503**
`{"error":"busy"}`.

The worker’s `for` loop does the “correct” HTTP thing: treat 5xx as
retryable, `continue` to the next handle, or wrap the client in Tenacity
`@retry(wait=wait_exponential(), stop=stop_after_attempt(5))`.

That path has three hidden properties:

1. **Each extra POST contends for the same lock.** The holder never
   finishes. 503 count *rises*. The sidecar looks hung.
2. **Backoff still starts the next handle** if you `continue` the outer
   loop. Exponential wait on the *same* URL is Tenacity’s job. Walking a
   batch is yours.
3. **A short client timeout orphans the lock.** If the client gives up at
   30s and the worker is allowed 60s, the scan keeps running. The next
   POST is 503. Per the Cynical0n3 NotebookLM (`systems`): that orphans
   the background lock, blows the token budget on useless retries, and
   grows KV-cache on an amnesiac loop that forgets it already tried.

The correct primitive is **break this cycle + later timer**, not retry.

---

## 2. Quantified incident (lab shape, no live host)

Twelve public handles, one single-flight sidecar, lock wait 2s then 503.
Handle `forge` is mid-scan when the worker starts the rest of the list.

| Step | Without this kernel | With this kernel |
| ---- | ------------------- | ---------------- |
| Handle 1 `forge` | POST `/scan` — lock acquired | Same |
| Handle 2 | 503 `busy` → `continue` | 503 → `busy` → **break** |
| Handles 3–12 | Ten more POSTs, all 503, ~2s each (~20s of contention) | **0** extra POSTs |
| Lock holder | Starved / looks hung | Finishes; next systemd/cron cycle resumes the list |
| After 3 consecutive hard | Worker still looping | `abort_sweep(3)` skips the rest of *this* sweep |

503 count after the fix should **fall**. If 503s rise with “more
parallelism,” you inverted the fix.

---

## 3. Real-world: Curiosity-Docker

The public sidecar returns 503 `{"error":"busy"}` after a short lock wait
(`shim_server.py`). Its START_HERE already says not to hammer every
100 ms. Its HTTP_API already names kinds (`busy` / `timeout` /
`transport`) and the timeout pair (**120s** client vs **60s** scan).

This repo is the **importable** form of that paragraph so a curiosity
worker cannot “forget” it in code review. Pair:
[Curiosity-Docker](https://github.com/CynicalTyr/Curiosity-Docker).

---

## 4. Real-world: cooldown stamps

If you increment `_last_ok` on *any* HTTP 200, empty and chat/no-JSON
look like success. If you increment only on hits, empty loops forever.
Count **attempts** toward the cap. Stamp long cooldowns only on
**parseable success**. Occupancy is neither success nor “no profiles.”

---

## 5. Real-world: Docker Desktop vs host network

Bridge NAT makes every client look like the proxy. People “fix” 403 with
`ALLOWED_IPS=*`. Combined with a WAN bind that is a public scanner.
Occupancy policy will not save a mis-bound port. Read Curiosity-Docker
security notes.

---

## How this stands out

Researched with Context7 (`libraryId=/jd/tenacity`
`retry_if_exception_type` / `retry_if_result` / `wait_exponential` /
`stop_after_attempt` — retries **one function**;
`libraryId=/urllib3/urllib3` `Retry.is_retry` +
`RETRY_AFTER_STATUS_CODES = frozenset([413, 429, 503])`;
`libraryId=/resilience4j/resilience4j` `RetryConfig` defaults
`DEFAULT_MAX_ATTEMPTS = 3`, `DEFAULT_WAIT_DURATION = 500` on the
decorated supplier) and GitHub-MCP (`jd/tenacity` file
`tenacity/retry.py`; `urllib3/urllib3` file `src/urllib3/util/retry.py`;
`resilience4j/resilience4j` file
`resilience4j-retry/.../RetryConfig.java`;
`CynicalTyr/Curiosity-Docker` files `START_HERE.md`, `docs/HTTP_API.md`,
`shim_server.py`). DeepWiki on `jd/tenacity` describes a Core Engine
that re-invokes the wrapped callable until stop/wait/retry strategies
agree — not an outer handle loop. GitHub `search_code` for
`should_break_handle_loop` and `"break_handle_loop"` returned **zero**
hits. Sibling kernels `epistemic-deny` and `agent-review-envelope` are
denies and speech queues, not occupancy.

| Obvious alternative | What they optimize | What they miss | This kernel |
| ------------------- | ------------------ | -------------- | ----------- |
| Tenacity `@retry` (`tenacity/retry.py`) | Re-call one function with stop/wait/retry strategies | 503 occupancy is not an exception to retry; backoff still hammers the **same** lock | Classify 503 as `busy`; **break** the handle list |
| urllib3 `Retry` (`src/urllib3/util/retry.py`) | Connection pooling + `status_forcelist` / Retry-After | **503 is in `RETRY_AFTER_STATUS_CODES`** — the HTTP client will retry occupancy as if it were overload | Do not put 503 in `status_forcelist` for a single-flight sidecar |
| Resilience4j `RetryConfig` | `maxAttempts` + `waitDuration` on a decorated supplier | CircuitBreaker records failures then **re-throws**; Retry still retries the same backend call | Occupancy is healthy lock, not a backend failure to decorate |
| Curiosity-Docker START_HERE | Sidecar + prose “do not tight-loop 503” | Prose is not an import; workers forget it | `should_break_handle_loop` + `abort_sweep(3)` |
| `epistemic-deny` (sibling) | Deny-as-packet | Occupancy is not a permission deny | This kernel is the lock classifier |
| `agent-review-envelope` (sibling) | Generator ≠ evaluator for *speech* | Queues do not stop a handle loop | File sitreps later; first **break** |

**Non-obvious / high-leverage:** the product is the **outer** `break`,
not another backoff curve. Client timeout **>** worker timeout is the
constant that decides whether a slow scan is `ok` or fake `timeout`.
Curiosity-Docker already documents 120s vs 60s; this kernel makes that
pair unskippable in the client.

**Mental model to replace:** adopters think 503 = retry (Tenacity,
urllib3, Resilience4j all agree). The governing model is **503 =
occupancy mutex — break the batch.** Per Cynical0n3 NotebookLM
(`systems`): retrying busy on a single-flight sidecar orphans locks
when the client is impatient, burns tokens, and the agent grades its
own loop as “working.”

**Incentive:** the stack will keep wrapping `/scan` in `@retry` because
it is cheaper than teaching the worker a lock, and because urllib3
already treats 503 as retryable.

**Second-order effect:** once copied, teams optimize handles-per-minute
and add a hammer MCP tool or shrink the client timeout so the demo is
never idle. That metric is the livelock. Count 503s after `break` vs
scans that complete. Do **not** add `occupancy_retry`.

---

## 6. Short comparison (same facts, operator table)

See **How this stands out** above for library/file evidence. In one line:
this is not a retry *framework*. It is a kernel you drop into the loop
you already have. You still write the timer that resumes the batch.

| Policy | Outcome |
| ------ | ------- |
| `continue` on timeout / 503 | Livelock, “hung” sidecar |
| Parallel scans | Same lock, more 503s |
| Tenacity / urllib3 Retry on 503 | Same call, lock never released |
| `break` + 3-hard abort | Lock holder finishes; sweep resumes later |

---

## 7. Architecture decisions worth copying

1. **Kinds, not status integers, in the loop.** `http_error` (one bad
   handle) may continue; `busy` / `timeout` / `transport` must break.
2. **Abort after three consecutive hard failures.** One 503 is occupancy;
   three in a row is “sidecar is gone — stop the sweep.”
3. **Client timeout > worker timeout.** Fake timeouts are occupancy in
   disguise.
4. **MCP classifies; it does not hammer.** Inspect tools only.

---

## 8. Measuring whether anyone *uses* this

Stars are vanity. Count:

- 503 responses per sweep **after** `break` ships (should fall).
- Scans that return 200 (empty or hits) vs POSTs issued during a lock.
- Client timeouts where client wait < worker cap (those are config bugs).
- MCP tool lists that contain a retry-busy primitive (those are bypasses).

---

## 9. Where this sits in the kernel family

Occupancy (this repo) + denies (`epistemic-deny`) + queues
(`agent-review-envelope`) are different layers of an autonomous
operator. The sidecar is [Curiosity-Docker](https://github.com/CynicalTyr/Curiosity-Docker).
The model is a tier inside that machine, not the machine.

## Hidden dynamics (short)

- Pattern: HTTP 503 on a single-flight sidecar is a mutex, not a flake. break, do not continue.
- Loop: continue on busy → more 503s → “hung” sidecar. break + later cycle → lock holder finishes.
- Incentive: Sweep success-rate metrics treat occupancy as failure, so people add Tenacity — the worst fix.
- Leverage: Client timeout must be *longer* than worker timeout (e.g. 120s vs 60s). Invert it and you fake transport death.
- Harness: MCP occupancy_classify after each scan. If break_handle_loop, the model must stop the batch this turn. No hammer-retry tool.
- Custom AI: Your HTTP worker maps status→kind, then break. systemd timer / cron runs the next cycle. No tight 503 loop.
