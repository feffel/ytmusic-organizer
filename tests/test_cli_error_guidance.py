import unittest

from ytmusic_organizer.cli import build_helpful_error


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


if __name__ == "__main__":
    unittest.main()
