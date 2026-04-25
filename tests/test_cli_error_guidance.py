import unittest
from io import StringIO
from pathlib import Path
import tempfile
from unittest.mock import patch

from ytmusic_organizer.cli import _warn_legacy_root_artifacts, build_helpful_error, main
from ytmusic_organizer.ui import WizardUI


class CliErrorGuidanceTests(unittest.TestCase):
    def test_auth_headers_invalid_has_actionable_guidance(self) -> None:
        msg = build_helpful_error(
            RuntimeError("AUTH_HEADERS_INVALID::Missing required header(s): cookie")
        )
        self.assertIn("Auth headers are incomplete or malformed", msg)
        self.assertIn("blank line", msg)
        self.assertIn("cookie, x-goog-authuser", msg)
        self.assertNotIn("ytmusicapi", msg)

    def test_auth_missing_includes_docs_and_fix_steps(self) -> None:
        msg = build_helpful_error(FileNotFoundError("Auth file not found: /tmp/missing.json"))
        self.assertIn("Auth file is missing", msg)
        self.assertIn("ytmo setup", msg)
        self.assertIn("ytmo setup --auth-file", msg)

    def test_setup_missing_includes_setup_command(self) -> None:
        msg = build_helpful_error(RuntimeError("Setup has not been completed. Run `ytmo setup`"))
        self.assertIn("Setup is incomplete", msg)
        self.assertIn("ytmo setup", msg)

    def test_api_key_missing_includes_env_hint(self) -> None:
        msg = build_helpful_error(RuntimeError("OPENAI_API_KEY is required for --mode api"))
        self.assertIn("OPENAI_API_KEY", msg)
        self.assertIn("--mode manual", msg)

    def test_invalid_json_input_guidance_avoids_stdin_jargon(self) -> None:
        msg = build_helpful_error(ValueError("Invalid JSON from stdin: Could not parse JSON"))
        self.assertIn("Plan output is not valid JSON", msg)
        self.assertNotIn("stdin", msg.lower())

    def test_keyboard_interrupt_has_helpful_message(self) -> None:
        msg = build_helpful_error(KeyboardInterrupt())
        self.assertIn("Operation cancelled by user", msg)
        self.assertIn("Re-run the same command", msg)

    def test_main_handles_keyboard_interrupt_without_traceback(self) -> None:
        capture = StringIO()
        with (
            patch("ytmusic_organizer.cli.run_demo", side_effect=KeyboardInterrupt()),
            patch("sys.stdout", capture),
            patch("ytmusic_organizer.cli.WizardUI.render_callout") as render_callout,
        ):
            code = main(["demo"])
        self.assertEqual(code, 1)
        self.assertEqual(render_callout.call_count, 1)
        args = render_callout.call_args.args
        self.assertEqual(args[0], "warning")
        self.assertEqual(args[1], "Operation cancelled")
        self.assertTrue(capture.getvalue().startswith("\n"))

    def test_setup_interruption_uses_styled_callout(self) -> None:
        capture = StringIO()
        with (
            patch(
                "ytmusic_organizer.cli.run_setup",
                side_effect=RuntimeError("Setup was interrupted. Re-run `ytmo setup` to resume."),
            ),
            patch("ytmusic_organizer.cli._warn_legacy_root_artifacts"),
            patch("ytmusic_organizer.cli.WizardUI.command_header"),
            patch("sys.stdout", capture),
            patch("ytmusic_organizer.cli.WizardUI.render_callout") as render_callout,
        ):
            code = main(["setup"])
        self.assertEqual(code, 1)
        self.assertEqual(render_callout.call_count, 1)
        args = render_callout.call_args.args
        self.assertEqual(args[0], "warning")
        self.assertEqual(args[1], "Setup interrupted")
        self.assertTrue(capture.getvalue().startswith("\n"))

    def test_legacy_root_artifact_warning_includes_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / "project"
            workspace = Path(tmp) / "workspace"
            cwd.mkdir()
            (cwd / "browser.json").write_text("{}", encoding="utf-8")
            capture = StringIO()
            with patch("sys.stdout", capture):
                _warn_legacy_root_artifacts(
                    WizardUI(enabled=True, force_tty=False), workspace=workspace, cwd=cwd
                )
            output = capture.getvalue()
            self.assertIn("Active workspace is", output)
            self.assertIn("Move or delete these old local files if they are stale", output)
            self.assertIn("pass --workspace", output)


if __name__ == "__main__":
    unittest.main()
