import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


class CopyConsistencyTests(unittest.TestCase):
    def test_cleanup_dry_run_uses_structured_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "cleanup",
                    "--workspace",
                    str(workspace),
                    "--dry-run",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Dry Run Summary", result.stdout)
            self.assertIn("Command", result.stdout)
            self.assertIn("cleanup", result.stdout)

    def test_stats_human_output_uses_friendly_plan_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "stats",
                    "--workspace",
                    str(workspace),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Needs plan file", result.stdout)
            self.assertNotIn("skipped_missing_plan", result.stdout)

    def test_manual_mode_prompt_avoids_stdin_jargon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "setup",
                    "--workspace",
                    str(workspace),
                ],
                check=False,
                capture_output=True,
                text=True,
                input="manual\n\n\n",
            )
            self.assertNotEqual(result.returncode, 0)
            combined = (result.stdout + result.stderr).lower()
            self.assertNotIn("stdin", combined)


if __name__ == "__main__":
    unittest.main()
