import contextlib
import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from ytmusic_organizer.config import Config, load_or_create_config, save_config
from ytmusic_organizer.workflows import ensure_bootstrap_completed, run_setup


class ConfigAndBootstrapTests(unittest.TestCase):
    @contextlib.contextmanager
    def _setup_mocks(self):
        def fake_export_liked(_yt, liked_path: Path):  # noqa: ANN001
            liked_path.parent.mkdir(parents=True, exist_ok=True)
            liked_path.write_text("[]", encoding="utf-8")
            return []

        def fake_obtain_full_plan(_mode, _config, paths, **_kwargs):  # noqa: ANN001
            paths.playlist_plan.parent.mkdir(parents=True, exist_ok=True)
            paths.playlist_plan.write_text('{"playlists": []}', encoding="utf-8")
            return {"playlists": []}

        def fake_update_managed_playlists(_results, managed_path: Path):  # noqa: ANN001
            managed_path.write_text('{"schema_version": 2, "playlists": []}', encoding="utf-8")
            return []

        def fake_initialize_state(_liked_path: Path, state_path: Path):  # noqa: ANN001
            state_path.write_text('{"processed_video_ids": []}', encoding="utf-8")

        with (
            patch("ytmusic_organizer.workflows.make_ytmusic", return_value=object()),
            patch("ytmusic_organizer.workflows.export_liked", side_effect=fake_export_liked),
            patch(
                "ytmusic_organizer.workflows._obtain_full_plan", side_effect=fake_obtain_full_plan
            ),
            patch(
                "ytmusic_organizer.workflows.update_managed_playlists",
                side_effect=fake_update_managed_playlists,
            ),
            patch(
                "ytmusic_organizer.workflows.apply_plan",
                return_value={"results": [], "missing": 0},
            ),
            patch(
                "ytmusic_organizer.workflows.initialize_state", side_effect=fake_initialize_state
            ),
        ):
            yield

    def test_config_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            cfg = Config(
                auth_file="browser.json", classification_mode="manual", openai_model="gpt-4.1-mini"
            )
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
                patch(
                    "ytmusic_organizer.workflows._obtain_full_plan", return_value={"playlists": []}
                ),
                patch("ytmusic_organizer.workflows.update_managed_playlists", return_value=[]),
                patch(
                    "ytmusic_organizer.workflows.apply_plan",
                    return_value={"results": [], "missing": 0},
                ),
                patch("ytmusic_organizer.workflows.initialize_state", return_value=None),
            ):
                result = run_setup(
                    workspace=workspace,
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
                    auth_file=None,
                    mode="manual",
                    interactive=False,
                )
            self.assertIn("Run interactive setup", str(ctx.exception))

    def test_setup_interactive_accepts_json_style_headers_for_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / ".ytmo"
            workspace.mkdir(parents=True, exist_ok=True)

            observed: dict[str, str] = {}

            def fake_setup(filepath: str | None = None, headers_raw: str | None = None):  # noqa: ANN001
                observed["headers_raw"] = headers_raw or ""
                Path(filepath or "").write_text("{}", encoding="utf-8")
                return headers_raw or ""

            pasted_lines = iter(
                [
                    "{",
                    '  "cookie": "a=b; c=d",',
                    '  "x-goog-authuser": "1",',
                    '  "x-origin": "https://music.youtube.com"',
                    "}",
                ]
            )

            def fake_input(prompt: str = "") -> str:  # noqa: ARG001
                try:
                    return next(pasted_lines)
                except StopIteration as exc:
                    raise EOFError from exc

            with (
                patch("builtins.input", side_effect=fake_input),
                patch("ytmusic_organizer.workflows.ytmusic_setup", side_effect=fake_setup),
                patch("ytmusic_organizer.workflows.make_ytmusic", return_value=object()),
                patch("ytmusic_organizer.workflows.export_liked", return_value=[]),
                patch(
                    "ytmusic_organizer.workflows._obtain_full_plan", return_value={"playlists": []}
                ),
                patch("ytmusic_organizer.workflows.update_managed_playlists", return_value=[]),
                patch(
                    "ytmusic_organizer.workflows.apply_plan",
                    return_value={"results": [], "missing": 0},
                ),
                patch("ytmusic_organizer.workflows.initialize_state", return_value=None),
            ):
                run_setup(
                    workspace=workspace,
                    auth_file=None,
                    mode="manual",
                    interactive=True,
                )

            self.assertIn("cookie: a=b; c=d", observed["headers_raw"])
            self.assertIn("x-goog-authuser: 1", observed["headers_raw"])

    def test_setup_interactive_truncated_headers_raise_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / ".ytmo"
            workspace.mkdir(parents=True, exist_ok=True)

            pasted_lines = iter(
                [
                    "cookie: a=b; c=d",
                ]
            )

            def fake_input(prompt: str = "") -> str:  # noqa: ARG001
                try:
                    return next(pasted_lines)
                except StopIteration as exc:
                    raise EOFError from exc

            with patch("builtins.input", side_effect=fake_input):
                with self.assertRaises(RuntimeError) as ctx:
                    run_setup(
                        workspace=workspace,
                        auth_file=None,
                        mode="manual",
                        interactive=True,
                    )
            self.assertIn(
                "AUTH_HEADERS_INVALID::Missing required header(s): x-goog-authuser",
                str(ctx.exception),
            )

    def test_setup_resume_replays_completed_steps_with_numbered_done_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".ytmo"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "browser.json").write_text("{}", encoding="utf-8")

            with self._setup_mocks():
                run_setup(
                    workspace=workspace,
                    auth_file=None,
                    mode="manual",
                    interactive=False,
                )

            capture = io.StringIO()
            with patch("sys.stdout", capture):
                with self._setup_mocks():
                    run_setup(
                        workspace=workspace,
                        auth_file=None,
                        mode="manual",
                        interactive=False,
                    )

            output = capture.getvalue()
            self.assertIn("Step 1/6 done | Auth check already completed", output)
            self.assertIn("Step 2/6 done | Export full liked songs already completed", output)
            self.assertIn("Step 6/6 done | Initialize incremental state already completed", output)
            self.assertNotIn("Resuming:", output)

    def test_setup_resume_reuses_saved_mode_without_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".ytmo"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "browser.json").write_text("{}", encoding="utf-8")

            with self._setup_mocks():
                run_setup(
                    workspace=workspace,
                    auth_file=None,
                    mode="manual",
                    interactive=False,
                )

            with patch(
                "builtins.input", side_effect=AssertionError("input() should not be called")
            ):
                with self._setup_mocks():
                    run_setup(
                        workspace=workspace,
                        auth_file=None,
                        mode=None,
                        interactive=True,
                    )


if __name__ == "__main__":
    unittest.main()
