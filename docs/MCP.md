# MCP adapter

This kernel is **not** the HTTP sidecar. It classifies occupancy so an IDE
agent cannot treat HTTP 503 as “try the next handle.”

```
MCP host (Claude Desktop, Cursor, custom runtime)
    │  stdio JSON-RPC
    ▼
examples/mcp_server.py     ← this repo, runs next to the agent
    │  classify_http / abort_sweep
    ▼
Your scan worker (HTTP) → e.g. Curiosity-Docker POST /scan
```

## Tools

| Tool | Returns |
| ---- | ------- |
| `occupancy_classify` | `{kind, break_handle_loop, hint}` |
| `occupancy_should_abort` | bool after N consecutive hard failures |

`occupancy_classify` arguments: `status` (int), `timed_out` (bool),
`transport_error` (bool).

## Install (agent host)

```bash
python3 -m pip install -r examples/requirements-mcp.txt
```

Copy `examples/mcp.example.json`. Absolute path to `mcp_server.py`.
Restart the host. Logs on stderr only.

## How agents should use the tools

1. After each scan HTTP result, call `occupancy_classify`.
2. If `break_handle_loop`, **stop the batch**.
3. If `occupancy_should_abort` is true, skip username discovery this cycle.

Sidecar HTTP contract: [Curiosity-Docker `docs/HTTP_API.md`](https://github.com/CynicalTyr/Curiosity-Docker/blob/main/docs/HTTP_API.md).
Worker loop recipes: [`INTEGRATION.md`](INTEGRATION.md).
