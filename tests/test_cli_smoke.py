import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


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


if __name__ == "__main__":
    unittest.main()
