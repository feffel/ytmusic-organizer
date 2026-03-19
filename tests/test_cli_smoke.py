import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from ytmusic_organizer import __version__


class CliSmokeTests(unittest.TestCase):
    def test_no_command_shows_top_level_help_on_error(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ytmusic_organizer.cli"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("error: the following arguments are required: command", result.stderr)
        self.assertIn("Most common commands:", result.stderr)
        self.assertIn("{setup,sync,rebuild,cleanup,demo,stats}", result.stderr)

    def test_top_level_unrecognized_arg_shows_top_level_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ytmusic_organizer.cli", "-q"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("error:", result.stderr)
        self.assertIn("Most common commands:", result.stderr)
        self.assertIn("{setup,sync,rebuild,cleanup,demo,stats}", result.stderr)

    def test_subcommand_unrecognized_arg_shows_subcommand_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ytmusic_organizer.cli", "setup", "-q"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("error: unrecognized arguments: -q", result.stderr)
        self.assertIn("usage: ytmo setup", result.stderr)
        self.assertIn("--auth-file", result.stderr)
        self.assertIn("--restart", result.stderr)

    def test_setup_invalid_mode_shows_setup_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ytmusic_organizer.cli", "setup", "--mode", "foo"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("error: argument --mode: invalid choice: 'foo'", result.stderr)
        self.assertIn("usage: ytmo setup", result.stderr)
        self.assertIn("--mode {manual,api}", result.stderr)

    def test_demo_invalid_mode_shows_demo_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ytmusic_organizer.cli", "demo", "--mode", "auto"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("error: argument --mode: invalid choice: 'auto'", result.stderr)
        self.assertIn("usage: ytmo demo", result.stderr)
        self.assertIn("--mode {manual,api}", result.stderr)

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
        self.assertIn("Most common commands:", result.stdout)
        self.assertIn("ytmo setup", result.stdout)
        self.assertIn("ytmo sync", result.stdout)
        self.assertIn("ytmo rebuild --dry-run", result.stdout)

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

    def test_rebuild_cancelled_uses_callout_style(self) -> None:
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
                ],
                check=False,
                capture_output=True,
                text=True,
                input="n\n",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Action cancelled", result.stdout)

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

    def test_cleanup_cancelled_uses_callout_style(self) -> None:
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
                ],
                check=False,
                capture_output=True,
                text=True,
                input="n\n",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Action cancelled", result.stdout)

    def test_demo_runs_with_default_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "demo",
                    "--workspace",
                    str(workspace),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Demo mode only", result.stdout)
            self.assertIn("Step 1/6", result.stdout)
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
                self.assertIn(f"Mode: {mode}", result.stdout)

    def test_demo_invalid_mode_returns_parse_error(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ytmusic_organizer.cli", "demo", "--mode", "auto"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)

    def test_stats_plain_output_uses_hero_secondary_footer_sections(self) -> None:
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
            self.assertIn("Status Overview", result.stdout)
            self.assertIn("Plan & Coverage", result.stdout)
            self.assertIn("Queue & Gaps", result.stdout)
            self.assertIn("Health Check", result.stdout)
            self.assertIn("Health:", result.stdout)


if __name__ == "__main__":
    unittest.main()
