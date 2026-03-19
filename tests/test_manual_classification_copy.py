from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from ytmusic_organizer.config import Config
from ytmusic_organizer.paths import WorkspacePaths
from ytmusic_organizer.workflows import _obtain_full_plan, _obtain_new_plan


class ManualClassificationCopyTests(unittest.TestCase):
    def test_full_plan_manual_callout_mentions_ai_tool_and_full_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = WorkspacePaths(Path(tmp))
            ui = Mock()
            prompt_path = Path(tmp) / "full_prompt.txt"
            with (
                patch("ytmusic_organizer.workflows.read_json_from_stdin", return_value={}),
                patch("ytmusic_organizer.workflows.validate_full_plan", return_value={}),
            ):
                _obtain_full_plan(
                    mode="manual",
                    config=Config(),
                    paths=paths,
                    ui=ui,
                    songs_override=[],
                    prompt_path=prompt_path,
                    persist_plan=False,
                )

            call_args = ui.render_callout.call_args
            self.assertIsNotNone(call_args)
            lines = call_args.args[2]
            self.assertTrue(any("Use this prompt with your AI tool." in line for line in lines))
            self.assertTrue(
                any("Paste back the full output JSON and press Enter." in line for line in lines)
            )

    def test_new_plan_manual_callout_mentions_ai_tool_and_full_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = WorkspacePaths(Path(tmp))
            ui = Mock()
            prompt_path = Path(tmp) / "new_prompt.txt"
            with (
                patch("ytmusic_organizer.workflows.read_json_from_stdin", return_value={}),
                patch("ytmusic_organizer.workflows.validate_new_plan", return_value={}),
            ):
                _obtain_new_plan(
                    mode="manual",
                    config=Config(),
                    paths=paths,
                    ui=ui,
                    songs_override=[],
                    managed_override=[],
                    prompt_path=prompt_path,
                    persist_plan=False,
                )

            call_args = ui.render_callout.call_args
            self.assertIsNotNone(call_args)
            lines = call_args.args[2]
            self.assertTrue(any("Use this prompt with your AI tool." in line for line in lines))
            self.assertTrue(
                any("Paste back the full output JSON and press Enter." in line for line in lines)
            )


if __name__ == "__main__":
    unittest.main()
