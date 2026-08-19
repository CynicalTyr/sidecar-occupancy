# Advanced: occupancy vs retries in agent OSINT loops

Search terms: *HTTP 503 busy sidecar agent*, *username discovery livelock*,
*Curiosity-Docker occupancy*, *client timeout longer than scan timeout*,
*do not continue on 503*.

---

## 1. Why this is not “just retry with backoff”

Retries are for **flakes**. Occupancy is a **mutex**. Exponential backoff
on 503 still starts the next handle while the lock is held if you
`continue` the for-loop. The correct primitive is **break + later cycle**
(systemd timer, cron, next heartbeat).

---

## 2. Real-world: Curiosity-Docker

The public sidecar returns 503 `{"error":"busy"}` after a short lock wait.
Its START_HERE already says not to hammer. This repo is the **importable**
form of that paragraph so a curiosity worker cannot “forget” it in code
review.

Pair: [Curiosity-Docker](https://github.com/CynicalTyr/Curiosity-Docker).

---

## 3. Real-world: cooldown stamps

If you increment `_last_ok` on *any* HTTP 200, empty and chat/no-JSON
look like success. If you increment only on hits, empty loops forever.
Count **attempts** toward the cap. Stamp long cooldowns only on
**parseable success**. Occupancy is neither success nor “no profiles.”

See `reviewer-not-extractor` (`cooldown_allowed(parse_succeeded=...)`).

---

## 4. Real-world: Docker Desktop vs host network

Bridge NAT makes every client look like the proxy. People “fix” 403 with
`ALLOWED_IPS=*`. Combined with a WAN bind that is a public scanner. Occupancy
policy will not save a mis-bound port. Read Curiosity-Docker security notes.

---

## 5. Comparison

| Policy | Outcome |
| ------ | ------- |
| `continue` on timeout | Livelock, “hung” sidecar |
| Parallel scans | Same lock, more 503s |
| `break` + 3-hard abort | Lock holder finishes; sweep resumes later |

---

## 6. Measuring use

503 count should **fall** after you ship `break`. If 503s rise with
“more parallelism,” you inverted the fix.

## Hidden dynamics (short)

- Pattern: HTTP 503 on a single-flight sidecar is a mutex, not a flake. break, do not continue.
- Loop: continue on busy → more 503s → “hung” sidecar. break + later cycle → lock holder finishes.
- Incentive: Sweep success-rate metrics treat occupancy as failure, so people add parallelism — the worst fix.
- Leverage: Client timeout must be *longer* than worker timeout (e.g. 120s vs 60s). Invert it and you fake transport death.
- Harness: MCP occupancy_classify after each scan. If break_handle_loop, the model must stop the batch this turn.
- Custom AI: Your HTTP worker maps status→kind, then break. systemd timer / cron runs the next cycle. No tight 503 loop.

