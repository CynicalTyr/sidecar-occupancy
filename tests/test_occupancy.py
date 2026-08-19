from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from occupancy import abort_sweep, classify_http, should_break_handle_loop


class OccupancyTests(unittest.TestCase):
    def test_503_is_busy_and_breaks(self) -> None:
        k = classify_http(503, timed_out=False, transport_error=False)
        self.assertEqual(k, "busy")
        self.assertTrue(should_break_handle_loop(k))

    def test_abort_after_three(self) -> None:
        self.assertFalse(abort_sweep(2))
        self.assertTrue(abort_sweep(3))


if __name__ == "__main__":
    unittest.main()
