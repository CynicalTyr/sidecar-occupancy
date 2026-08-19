#!/usr/bin/env python3
"""MCP: classify sidecar HTTP so the model cannot treat 503 as 'try next handle'."""
from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pip install 'sidecar-occupancy[mcp]'") from exc

from occupancy import abort_sweep, classify_http, should_break_handle_loop

mcp = FastMCP("sidecar-occupancy")


@mcp.tool()
def occupancy_classify(status: int = 0, timed_out: bool = False, transport_error: bool = False) -> dict:
    """Map HTTP/timeout into ok|empty|busy|timeout|transport|http_error."""
    kind = classify_http(status or None, timed_out=timed_out, transport_error=transport_error)
    return {
        "kind": kind,
        "break_handle_loop": should_break_handle_loop(kind),
        "abort_if_three_hard": True,
        "hint": "On busy/timeout/transport: STOP this batch. Do not continue to the next handle.",
    }


@mcp.tool()
def occupancy_should_abort(consecutive_hard: int) -> bool:
    """True after three consecutive busy/timeout/transport results."""
    return abort_sweep(int(consecutive_hard))


if __name__ == "__main__":
    mcp.run()
