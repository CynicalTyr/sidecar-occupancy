# START HERE

**If you only open one file, open this one.**

This guide assumes you can log into a computer, open a terminal, and paste
commands. It does **not** assume you know Docker, MCP, or how AI agents work.

**One sentence:** HTTP 503 on a single-flight sidecar is a mutex, not a flake.

## Who this helps

| Who | What they get |
| --- | --- |
| **You (learning)** | A 10-minute proof the code runs (`smoke ok`). |
| **An AI harness** | Cursor, Claude Desktop, Copilot Chat — a program that runs a model *and* tools. See §5. |
| **A locally built AI** | A Python worker *you* wrote (cron, systemd, a script). See §6. |
| **People talking to that AI** | Fewer silent failures, surprise pages, and invented facts. |

---

## 0. Words you will see

| Word | Plain meaning |
| ---- | ------------- |
| **Harness** | The IDE or app that hosts the model (Cursor, Claude Desktop). It starts extra programs called **MCP tools**. |
| **MCP** | A way for the model to call small tools. Those tools must not be “send Slack” unless you mean it. |
| **Locally built AI** | Your own loop: your code calls models and functions. You decide the order. |
| **Kernel** | This tiny library. It is not a full chatbot. You drop it into *your* loop. |

Files in this folder: `README.md` (why it exists), `examples/quickstart.py` (first demo),
`tests/` (proof), `docs/ADVANCED.md` (evergreen tutorials), `docs/INTEGRATION.md` (recipes).

---

## 1. What you need

- Python 3.10 or newer. Check: `python3 -V`
- Ability to `cd` into this folder
- A throwaway directory for any `AGENT_HOME` (use `/tmp/...`, never a real home)

No GPU. No API keys for the 10-minute path.

---

## 2. First success (under 10 minutes)

```bash
cd occupancy-break
chmod +x scripts/smoke.sh
./scripts/smoke.sh
```

You want a line `smoke ok:` and no traceback. That script sets `PYTHONPATH`
for you. Optional later: `python3 -m pip install -e .`

**This kernel’s success looks like:** Printed kind: busy, break loop: True (from HTTP 503).

If `python3` is missing, install Python from python.org or your package
manager, then try again.

---

## 3. How to edit (safe)

Edit files in *this* folder. Re-run `./scripts/smoke.sh`. Do not copy this
folder over a live operator machine “to try it.”

---

## 4. Configure

Read `docs/INTEGRATION.md` for env names. There is no production `.env` in
git on purpose.

---

## 5. Tie-in: AI harness (Cursor / Claude Desktop / MCP)

A harness does **not** magically import this folder. You either:

1. Add an MCP server from `examples/mcp_server.py` **if this kernel has one**
   (review-envelope and occupancy-break do — see `docs/MCP.md`), or
2. Keep the kernel in **your daemon**. The chat model only *inspects* results.

> MCP occupancy_classify after each scan. If break_handle_loop, the model must stop the batch this turn.

Paste-ready: tell the model the **policy** in `README.md` (“what others will
discover”). Do not give it a tool that bypasses the kernel.

---

## 6. Tie-in: locally built AI (no harness required)

Your script imports the module and calls the functions. That is the intended
path for most kernels.

> Your HTTP worker maps status→kind, then break. systemd timer / cron runs the next cycle. No tight 503 loop.

Copy `examples/quickstart.py` into your worker, then replace the demo
arguments with your IDs, tools, and paths.

---

## 7. Practice drills (do these once)

1. Classify 503 → busy and should_break_handle_loop True.
2. abort_sweep(2) is False; abort_sweep(3) is True.
3. Read Curiosity-Docker START_HERE: client timeout 120s vs scan 60s.

4. Re-run `./scripts/smoke.sh`. It must still pass.
5. Open `docs/ADVANCED.md` once (evergreen / search tutorial).

---

## 8. When something is wrong

| Symptom | Try |
| ------- | --- |
| `No module named ...` | Run `./scripts/smoke.sh` from *this* folder (it sets PYTHONPATH), or `pip install -e .` |
| `Permission denied` on smoke.sh | `chmod +x scripts/smoke.sh` |
| MCP tools missing | Absolute path to `examples/mcp_server.py`; restart the harness |
| Model ignores the kernel | The result never reached the tool channel — see INTEGRATION |

---

## 9. What not to do

- Do not skip the kernel “just this once” (that is how dual-control dies).
- Do not commit secrets, phones, or live identity YAML.
- Do not treat first success as production-ready without INTEGRATION.

**Risk to remember:** ALLOWED_IPS=* plus WAN bind “to fix 403” publishes a scanner. Occupancy will not save a mis-bound port.

---

## 10. Where to go next

| Need | Open |
| ---- | ---- |
| Why this exists / hidden dynamics | [`README.md`](README.md) |
| Recipes for harness + custom AI | [`docs/INTEGRATION.md`](docs/INTEGRATION.md) |
| Advanced / search tutorials | [`docs/ADVANCED.md`](docs/ADVANCED.md) |
| Extra | Sibling already public: [Curiosity-Docker START_HERE](https://github.com/CynicalTyr/Curiosity-Docker/blob/main/START_HERE.md). |

You are done with first use when smoke prints `ok` and you can say in one
sentence whether **your** agent is a harness, a custom loop, or both.
