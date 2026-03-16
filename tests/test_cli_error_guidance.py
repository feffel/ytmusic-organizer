import unittest

from ytmusic_organizer.cli import build_helpful_error


class CliErrorGuidanceTests(unittest.TestCase):
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

    def test_preview_missing_plan_is_actionable(self) -> None:
        msg = build_helpful_error(
            RuntimeError("PREVIEW_MISSING_PLAN::/tmp/ws/data/playlist_plan.json::workspace=/tmp/ws")
        )
        self.assertIn("Preview prerequisites are missing", msg)
        self.assertIn("Plan file not found", msg)
        self.assertIn("ytmo preview --plan", msg)

    def test_preview_missing_liked_snapshot_is_actionable(self) -> None:
        msg = build_helpful_error(
            RuntimeError("PREVIEW_MISSING_LIKED::/tmp/ws/data/liked_songs.json::workspace=/tmp/ws")
        )
        self.assertIn("Preview prerequisites are missing", msg)
        self.assertIn("Liked songs snapshot not found", msg)
        self.assertIn("ytmo setup", msg)


if __name__ == "__main__":
    unittest.main()
