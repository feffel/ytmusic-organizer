import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


class CliJsonOutputTests(unittest.TestCase):
    def test_cleanup_local_only_json_success(self) -> None:
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
                    "--local-only",
                    "--yes",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["command"], "cleanup")
            self.assertIn("removed_local_files", payload["result"])

    def test_setup_json_error_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            missing_auth = Path(tmp) / "missing-browser.json"
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
                    str(missing_auth),
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["command"], "setup")
            self.assertIn("Auth file is missing", payload["error"])


if __name__ == "__main__":
    unittest.main()
