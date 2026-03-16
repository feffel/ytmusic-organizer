import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from ytmusic_organizer import __version__


class CliSmokeTests(unittest.TestCase):
    def test_help_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ytmusic_organizer.cli", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("sync", result.stdout)
        self.assertIn("cleanup", result.stdout)
        self.assertIn("--version", result.stdout)
        self.assertIn(__version__, result.stdout)
        self.assertNotIn("preview", result.stdout)

    def test_version_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ytmusic_organizer.cli", "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(__version__, result.stdout)

    def test_setup_accepts_workspace_after_subcommand(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            auth = Path(tmp) / "missing-browser.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "setup",
                    "--workspace",
                    str(workspace),
                    "--non-interactive",
                    "--auth-file",
                    str(auth),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 2, msg=result.stderr)
            self.assertIn("Auth file is missing", result.stderr)

    def test_reset_cancelled_warning_renders_on_new_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [sys.executable, "-m", "ytmusic_organizer.cli", "reset", "--workspace", str(workspace)],
                check=False,
                capture_output=True,
                text=True,
                input="n\n",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("\nWARN Cancelled.", result.stdout)

    def test_cleanup_cancelled_warning_renders_on_new_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [sys.executable, "-m", "ytmusic_organizer.cli", "cleanup", "--workspace", str(workspace)],
                check=False,
                capture_output=True,
                text=True,
                input="n\n",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("\nWARN Cancelled.", result.stdout)


if __name__ == "__main__":
    unittest.main()
