import unittest

from ytmusic_organizer.cli import build_helpful_error


class CliErrorGuidanceTests(unittest.TestCase):
    def test_auth_missing_includes_docs_and_fix_steps(self) -> None:
        msg = build_helpful_error(FileNotFoundError("Auth file not found: /tmp/missing.json"))
        self.assertIn("Auth file is missing", msg)
        self.assertIn("README.md", msg)
        self.assertIn("ytmo init --auth-file", msg)

    def test_bootstrap_missing_includes_bootstrap_command(self) -> None:
        msg = build_helpful_error(RuntimeError("Bootstrap has not been completed. Run `ytmo init --bootstrap`"))
        self.assertIn("Bootstrap setup is incomplete", msg)
        self.assertIn("ytmo init --bootstrap", msg)

    def test_api_key_missing_includes_env_hint(self) -> None:
        msg = build_helpful_error(RuntimeError("OPENAI_API_KEY is required for --mode api"))
        self.assertIn("OPENAI_API_KEY", msg)
        self.assertIn("--mode manual", msg)


if __name__ == "__main__":
    unittest.main()
