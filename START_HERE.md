# START HERE

**If you only open one file, open this one.**

This guide assumes you can log into a computer, open a terminal, and paste
commands. It does **not** assume you know Docker, MCP, or how AI agents work.

HTTP 503 on a single-flight sidecar is a mutex, not a
flake — this library tells your loop to **break**, not retry.

## Who this helps

| Who | What they get |
| --- | --- |
| **You (learning)** | A 10-minute proof the code runs (`smoke ok`) and `503 → busy → break`. |
| **An AI harness** | Cursor, Claude Desktop, Copilot Chat — a program that runs a model *and* tools. See §5. |
| **A locally built AI** | Your own Python/timer worker. HTTP or function calls. MCP is optional. See §6. |
| **People talking to that AI** | Fewer silent hangs while one scan holds the lock. |

A **harness** is Cursor / Claude Desktop / VS Code Copilot — a program that
runs a model and **tools**. A **custom-built AI** is your own Python/timer
worker; HTTP or function calls; MCP optional.

---

## 0. Words you will see, then files

| Word | Plain meaning |
| ---- | ------------- |
| **Harness** | The IDE or app that hosts the model (Cursor, Claude Desktop). It can start **MCP tools**. |
| **MCP** | A way for the model to call small tools. Tools are not automatically safe. |
| **Locally built AI** | Your own loop: your code calls models and functions. You decide the order. |
| **Kernel** | This tiny library. It is not a full chatbot. |
| **Occupancy** | Another job already holds the sidecar lock. HTTP 503 `busy` is healthy. |
| **Break** | Stop walking more handles *this cycle*. Schedule the next cycle later. |

| File | What it does | What you change it for | How it helps agents / users |
| ---- | ------------ | ---------------------- | --------------------------- |
| `START_HERE.md` | This first-use guide | You usually do not | Humans: how to get `smoke ok` |
| `README.md` | Product + hidden dynamics | Forks / rename | Humans: “is this the right tool?” |
| `docs/INTEGRATION.md` | HTTP worker + MCP recipes | New host | Custom AI *and* harness |
| `docs/ADVANCED.md` | Why 503 retry livelocks (search article) | Architecture debates | People who already had the hang |
| `docs/MCP.md` | Classify / abort inspect tools | Tool names | Harness agents — **no hammer-retry** |
| `occupancy.py` | Classify + break + abort | Kinds (rarely) | The worker’s occupancy gate |
| `examples/quickstart.py` | First 503 → busy | Learning | Proof without a live sidecar |
| `examples/mcp_server.py` | MCP child process | Tool names | Harness *classifies* results |
| `examples/mcp.example.json` | Host config template | Absolute paths | Paste into Cursor / Claude Desktop |
| `tests/` | Contract tests | Behavior changes | 503 still breaks; abort still at 3 |
| `scripts/smoke.sh` | unittest + quickstart | CI locally | 10-minute first success |
| `.env.example` | Env **names** | Copy to `.env` (never commit `.env`) | Client timeout **>** worker timeout |

**Mental picture:**

```
Handle list  →  HTTP /scan  →  classify_http  →  busy? break the loop
Harness (optional)  →  occupancy_classify  →  same kinds (inspect / classify only)
Later cycle (timer / cron)  →  try the remaining handles
```

---

## 1. What you need

- Python 3.10 or newer. Check: `python3 -V`
- Ability to `cd` into this folder (the clone root)
- A throwaway directory for any `AGENT_HOME` (use `/tmp/...`, never a real home)

No GPU. No Docker. No API keys for the 10-minute path. A live sidecar is
optional; smoke does not need the network.

---

## 2. First success (under 10 minutes)

From **this folder** (after clone it is named `occupancy-break` or
`sidecar-occupancy`):

```bash
chmod +x scripts/smoke.sh
./scripts/smoke.sh
```

You want a line `smoke ok` and no traceback. That script sets `PYTHONPATH`
for you. Optional later:

```bash
python3 -m pip install -e .
cp .env.example .env
python3 examples/quickstart.py
```

**This kernel’s success looks like:** printed `kind: busy`, `break loop:
True` (from HTTP 503), and `abort sweep after 3: True`.

If `python3` is missing, install Python from python.org or your package
manager, then try again.

---

## 3. How to edit (safe)

Change Python files in *this* folder. Re-run `./scripts/smoke.sh`.

If you use MCP, **restart the harness** after editing
`examples/mcp_server.py` (the child process is already running). Do not
copy this folder over a live operator machine “to try it.”

---

## 4. Configure

Copy `.env.example` to `.env` if you want named timeout knobs for *your*
HTTP worker. Fill **names you own**. Never commit `.env`.

This library itself has no production token. The pair that matters when you
call a sidecar is:

- worker / scan cap (example name `USERNAME_DISCOVERY_SCAN_TIMEOUT`, often **60s**)
- client wait (example name `USERNAME_DISCOVERY_TIMEOUT`, often **120s**)

Keep the **client longer than the worker**. Invert that and a slow-but-finishing
scan becomes a fake `timeout`.

---

## 5. Using this with an AI harness (Cursor / Claude Desktop / MCP)

A **harness** is the program that runs the model and its tools. It does
**not** magically import this folder. You either:

1. Add an MCP server from `examples/mcp_server.py` (see `docs/MCP.md`) —
   **classify / abort only**, or
2. Keep the kernel in **your daemon**. The chat model only *inspects* results.

The MCP Python SDK keeps logs on **stderr** so stdout stays a JSON-RPC
pipe. Use an **absolute** path in the host config. Restart the harness
after edits.

Paste-ready policy:

> After each scan HTTP result, call occupancy_classify. If
> break_handle_loop is true, stop the handle batch this turn. Do not
> continue to the next username. Do not ask for a retry-busy or hammer
> tool. Client timeout must stay longer than the worker scan timeout.
> Hits are unverified public URLs.

There is **no** `occupancy_retry` tool on purpose.

---

## 6. Using this with a locally built AI (no MCP)

Your worker process maps HTTP → kind, then `should_break_handle_loop`.
A *different* timer (systemd, cron, next heartbeat) runs the next cycle.
The chat model is **not** that worker.

```python
from occupancy import classify_http, should_break_handle_loop, abort_sweep

kind = classify_http(status, timed_out=timed_out, transport_error=transport_error)
if should_break_handle_loop(kind):
    break  # end this cycle; do not continue
```

Copy `examples/quickstart.py` into your worker, then replace the demo
arguments with your status codes. Do **not** wrap `/scan` in Tenacity
`@retry` for 503.

Recipes: [`docs/INTEGRATION.md`](docs/INTEGRATION.md).

---

## 7. Practice drills (do these once)

1. Classify 503 → `busy` and `should_break_handle_loop` True.
2. `abort_sweep(2)` is False; `abort_sweep(3)` is True.
3. Confirm `examples/mcp_server.py` has **no** retry / hammer tool — only
   `occupancy_classify` and `occupancy_should_abort`.
4. Re-run `./scripts/smoke.sh`. It must still pass.
5. Open `docs/ADVANCED.md` once (evergreen / search tutorial). Read the
   timeout rule: client **120s** vs worker **60s**.

---

## 8. When something is wrong

| Symptom | Try |
| ------- | --- |
| `No module named ...` | Run `./scripts/smoke.sh` from *this* folder (it sets PYTHONPATH), or `pip install -e .` |
| `Permission denied` on smoke.sh | `chmod +x scripts/smoke.sh` |
| MCP tools missing | Absolute path to `examples/mcp_server.py`; restart the harness |
| MCP host “won’t connect” | No prints on stdout; SDK logs to stderr |
| Model keeps scanning after 503 | Result never reached the tool channel, or someone added a retry tool — see INTEGRATION |
| Slow scans look like `timeout` | Client timeout is shorter than the worker cap — invert it |

---

## 9. What not to do

- Do not skip the kernel “just this once” (that is how livelock returns).
- Do not commit secrets, phones, or live identity YAML.
- Do not add an MCP tool that retries 503 in a tight loop.
- Do not wrap occupancy in Tenacity / urllib3 `Retry` on 503.
- Do not set client timeout **shorter** than the worker scan timeout.
- Do not treat first success as production-ready without INTEGRATION.

**Risk to remember:** `ALLOWED_IPS=*` plus WAN bind “to fix 403” publishes
a scanner. Occupancy will not save a mis-bound port.

---

## 10. Where to go next

| Need | Open |
| ---- | ---- |
| Why this exists / hidden dynamics | [`README.md`](README.md) |
| Recipes for harness + custom AI | [`docs/INTEGRATION.md`](docs/INTEGRATION.md) |
| Advanced / search tutorials | [`docs/ADVANCED.md`](docs/ADVANCED.md) |
| MCP inspect tools | [`docs/MCP.md`](docs/MCP.md) |
| The sidecar this policy wraps | [Curiosity-Docker START_HERE](https://github.com/CynicalTyr/Curiosity-Docker/blob/main/START_HERE.md) |

You are done with first use when smoke prints `smoke ok` and you can say in one
sentence whether **your** agent is a harness, a custom loop, or both.
