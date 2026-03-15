import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from ytmusic_organizer.config import Config, load_or_create_config, save_config
from ytmusic_organizer.workflows import ensure_bootstrap_completed, run_setup


class ConfigAndBootstrapTests(unittest.TestCase):
    def test_config_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            cfg = Config(auth_file="browser.json", classification_mode="manual", openai_model="gpt-4.1-mini")
            save_config(path, cfg)
            loaded = load_or_create_config(path)
            self.assertEqual(loaded, cfg)

    def test_bootstrap_guard_blocks_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "bootstrap.json"
            with self.assertRaises(RuntimeError) as ctx:
                ensure_bootstrap_completed(marker)
            self.assertIn("ytmo setup", str(ctx.exception))

    def test_setup_resolves_relative_auth_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / ".ytmo"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "browser.json").write_text("{}", encoding="utf-8")

            with (
                patch("ytmusic_organizer.workflows.make_ytmusic", return_value=object()),
                patch("ytmusic_organizer.workflows.export_liked", return_value=[]),
                patch("ytmusic_organizer.workflows._obtain_full_plan", return_value={"playlists": []}),
                patch("ytmusic_organizer.workflows.update_managed_playlists", return_value=[]),
                patch("ytmusic_organizer.workflows.apply_plan", return_value={"results": [], "missing": 0}),
                patch("ytmusic_organizer.workflows.initialize_state", return_value=None),
            ):
                result = run_setup(
                    workspace=workspace,
                    cwd=root / "another-cwd",
                    auth_file=None,
                    mode="manual",
                    interactive=False,
                )
            self.assertEqual(result["workspace"], str(workspace))

    def test_setup_non_interactive_missing_auth_gives_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / ".ytmo"
            workspace.mkdir(parents=True, exist_ok=True)
            with self.assertRaises(FileNotFoundError) as ctx:
                run_setup(
                    workspace=workspace,
                    cwd=root,
                    auth_file=None,
                    mode="manual",
                    interactive=False,
                )
            self.assertIn("Run interactive setup", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
