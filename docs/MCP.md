# MCP adapter

This kernel is **not** the HTTP sidecar. It classifies occupancy so an IDE
agent cannot treat HTTP 503 as “try the next handle.”

```
MCP host (Claude Desktop, Cursor, custom runtime)
    │  stdio JSON-RPC
    ▼
examples/mcp_server.py     ← this repo, runs next to the agent
    │  classify_http / abort_sweep   (inspect / classify only)
    ▼
Your scan worker (HTTP) → e.g. Curiosity-Docker POST /scan
```

Keeping MCP to **classify / abort** means:

- The chat model cannot hammer a locked sidecar by “helping.”
- There is **no** `occupancy_retry` / tight-loop tool. Do not add one.
- Stdout of the MCP process stays a clean JSON-RPC pipe (log to stderr).

## Tools

| Tool | Returns |
| ---- | ------- |
| `occupancy_classify` | `{kind, break_handle_loop, hint}` |
| `occupancy_should_abort` | bool after N consecutive hard failures |

`occupancy_classify` arguments: `status` (int), `timed_out` (bool),
`transport_error` (bool).

Do **not** add a tool that POSTs `/scan` in a retry loop. The worker
already has HTTP. MCP only labels the result.

## Install (agent host)

```bash
python3 -m pip install -r examples/requirements-mcp.txt
```

Copy `examples/mcp.example.json`. Use an **absolute** path to
`examples/mcp_server.py`. Restart the MCP host after editing. Only the
MCP SDK may write to stdout.

## How agents should use the tools

1. After each scan HTTP result, call `occupancy_classify`.
2. If `break_handle_loop`, **stop the batch**.
3. If `occupancy_should_abort` is true, skip username discovery this cycle.
4. Do **not** ask for a retry-busy tool.

Sidecar HTTP contract: [Curiosity-Docker `docs/HTTP_API.md`](https://github.com/CynicalTyr/Curiosity-Docker/blob/main/docs/HTTP_API.md).
Worker loop recipes: [`INTEGRATION.md`](INTEGRATION.md).
