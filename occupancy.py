"""Occupancy kinds for a locked sidecar (username-discovery class).

When a worker holds a single-flight lock, extra clients must not
``continue`` the handle list. They should classify the failure and
``break`` the sweep after a streak of hard failures.

This is the unique lesson from an OSINT sidecar: HTTP 503 + a lock is
*healthy occupancy*, not transport death. Treating it as retry-able
``continue`` livelocks the lock holder.
"""

from __future__ import annotations

from typing import Literal

SidecarKind = Literal["ok", "empty", "busy", "timeout", "transport", "http_error"]

HARD_FAILURE_KINDS = frozenset({"busy", "timeout", "transport"})


def classify_http(status: int | None, *, timed_out: bool, transport_error: bool) -> SidecarKind:
    if transport_error:
        return "transport"
    if timed_out:
        return "timeout"
    if status == 503:
        return "busy"
    if status is not None and status >= 400:
        return "http_error"
    if status == 200:
        return "ok"
    return "empty"


def should_break_handle_loop(kind: SidecarKind) -> bool:
    """True → stop walking more handles this cycle (do not ``continue``)."""
    return kind in HARD_FAILURE_KINDS


def abort_sweep(consecutive_hard: int, *, threshold: int = 3) -> bool:
    """After N consecutive busy/timeout/transport, abandon the whole sweep."""
    return consecutive_hard >= threshold
