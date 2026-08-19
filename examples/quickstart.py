#!/usr/bin/env python3
from occupancy import abort_sweep, classify_http, should_break_handle_loop

kind = classify_http(503, timed_out=False, transport_error=False)
print("kind:", kind)
print("break loop:", should_break_handle_loop(kind))
print("abort sweep after 3:", abort_sweep(3))
