from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from ytmusic_organizer.io_utils import atomic_write_text


class AtomicWriteTests(unittest.TestCase):
    def test_atomic_write_failure_keeps_original_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "state.json"
            target.write_text('{"processed_video_ids":["old"]}', encoding="utf-8")

            with patch("pathlib.Path.replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaises(OSError):
                    atomic_write_text(target, '{"processed_video_ids":["new"]}', encoding="utf-8")

            self.assertEqual(
                target.read_text(encoding="utf-8"),
                '{"processed_video_ids":["old"]}',
            )
            leftovers = list(root.glob(".state.json.*.tmp"))
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
