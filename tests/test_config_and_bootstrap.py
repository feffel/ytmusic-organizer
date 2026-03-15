import tempfile
from pathlib import Path
import unittest

from ytmusic_organizer.config import Config, load_or_create_config, save_config
from ytmusic_organizer.workflows import ensure_bootstrap_completed, run_init


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
            self.assertIn("init --bootstrap", str(ctx.exception))

    def test_init_resolves_relative_auth_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / ".ytmo"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "browser.json").write_text("{}", encoding="utf-8")

            result = run_init(
                workspace=workspace,
                cwd=root / "another-cwd",
                auth_file=None,
                mode="manual",
                bootstrap=False,
                interactive=False,
            )
            self.assertEqual(result["workspace"], str(workspace))


if __name__ == "__main__":
    unittest.main()
