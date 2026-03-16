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
        self.assertIn("rebuild", result.stdout)
        self.assertIn("cleanup", result.stdout)
        self.assertIn("demo", result.stdout)
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

    def test_rebuild_cancelled_warning_renders_on_new_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [sys.executable, "-m", "ytmusic_organizer.cli", "rebuild", "--workspace", str(workspace)],
                check=False,
                capture_output=True,
                text=True,
                input="n\n",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("\nWARN Cancelled.", result.stdout)

    def test_reset_command_is_removed(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ytmusic_organizer.cli", "reset"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)

    def test_rebuild_dry_run_skips_yes_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "rebuild",
                    "--workspace",
                    str(workspace),
                    "--dry-run",
                    "--non-interactive",
                ],
                check=False,
                capture_output=True,
                text=True,
                input='{"playlists": []}\n',
            )
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("--yes is required", result.stderr)
            self.assertIn("Auth file is missing", result.stderr)

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

    def test_demo_runs_with_default_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [sys.executable, "-m", "ytmusic_organizer.cli", "demo", "--workspace", str(workspace)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("DEMO ONLY", result.stdout)
            self.assertFalse(workspace.exists())

    def test_demo_runs_for_manual_and_api_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            for mode in ("manual", "api"):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "ytmusic_organizer.cli",
                        "demo",
                        "--workspace",
                        str(workspace),
                        "--mode",
                        mode,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertIn(f"Classification mode (simulated): {mode}", result.stdout)

    def test_demo_invalid_mode_returns_parse_error(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ytmusic_organizer.cli", "demo", "--mode", "auto"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
