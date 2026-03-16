import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from ytmusic_organizer.workflows import run_demo


class DemoTests(unittest.TestCase):
    def test_run_demo_has_no_workspace_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = run_demo(workspace=workspace, mode="manual", emit_ui=False)
            self.assertFalse(workspace.exists())
            self.assertTrue(result["simulated"])
            self.assertEqual(result["mode"], "manual")

    def test_run_demo_does_not_call_side_effect_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            with (
                patch("ytmusic_organizer.workflows.ytmusic_setup", side_effect=AssertionError("no auth setup")),
                patch("ytmusic_organizer.workflows.make_ytmusic", side_effect=AssertionError("no ytmusic client")),
                patch("ytmusic_organizer.workflows.export_liked", side_effect=AssertionError("no export_liked")),
                patch("ytmusic_organizer.workflows.export_new_likes", side_effect=AssertionError("no export_new_likes")),
                patch("ytmusic_organizer.workflows.apply_plan", side_effect=AssertionError("no apply_plan")),
                patch("ytmusic_organizer.workflows.apply_new_likes", side_effect=AssertionError("no apply_new_likes")),
                patch("ytmusic_organizer.workflows.initialize_state", side_effect=AssertionError("no initialize_state")),
                patch("ytmusic_organizer.workflows.classify_with_openai", side_effect=AssertionError("no openai")),
                patch("ytmusic_organizer.workflows.save_config", side_effect=AssertionError("no config writes")),
            ):
                result = run_demo(workspace=workspace, mode="api", emit_ui=False)
            self.assertFalse(workspace.exists())
            self.assertTrue(result["simulated"])
            self.assertEqual(result["mode"], "api")


if __name__ == "__main__":
    unittest.main()
