from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from ytmusic_organizer.ui import WizardUI


class UISurfaceTests(unittest.TestCase):
    def _sample_result(self) -> dict:
        return {
            "processed_likes": 120,
            "managed_playlists": 7,
            "missing_matches": 3,
            "new_likes_pending": 4,
            "liked_snapshot_count": 150,
            "artifact_presence": {
                "config": True,
                "state": True,
                "managed_playlists": True,
                "liked_songs": True,
                "new_likes": True,
                "playlist_plan": True,
                "new_plan": True,
                "missing_matches": True,
            },
            "plan_diagnostics": {"status": "ok", "matched": 60, "missing": 3, "loose": 2, "ambiguous": 1},
            "insights": {
                "identity_score": 92,
                "plan_playlists": 7,
                "top_playlists": [{"name": "Night Drive", "songs": 18}],
                "coverage_ratio": 0.82,
                "collection_shape": "Growing catalog",
                "pending_momentum": "Steady momentum",
            },
            "warnings": [],
        }

    def test_show_stats_uses_staged_animation_in_rich_tty_mode(self) -> None:
        with (
            patch("ytmusic_organizer.ui.Console"),
            patch("ytmusic_organizer.ui.Live", create=True) as live_cls,
            patch("ytmusic_organizer.ui.time.sleep") as sleep_mock,
        ):
            live = live_cls.return_value.__enter__.return_value
            ui = WizardUI(enabled=True, force_tty=True)
            ui.show_stats(self._sample_result())
            self.assertEqual(live_cls.call_count, 1)
            self.assertEqual(live.update.call_count, 4)
            self.assertEqual(sleep_mock.call_count, 4)
            self.assertEqual(sleep_mock.call_args_list[0].args[0], 0.25)
            self.assertEqual(sleep_mock.call_args_list[1].args[0], 0.18)
            self.assertEqual(sleep_mock.call_args_list[2].args[0], 0.18)
            self.assertEqual(sleep_mock.call_args_list[3].args[0], 0.12)

    def test_show_stats_plain_mode_uses_layout_sections(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.show_stats(self._sample_result())
        output = capture.getvalue()
        self.assertIn("Identity Hero", output)
        self.assertIn("Shape + Momentum", output)
        self.assertIn("Highlights", output)
        self.assertIn("Health Footer", output)
        self.assertNotIn("Diagnostics:", output)

    def test_show_stats_sparse_mode_de_emphasizes_zeros(self) -> None:
        sparse = self._sample_result()
        sparse.update(
            {
                "processed_likes": 0,
                "managed_playlists": 0,
                "new_likes_pending": 0,
                "liked_snapshot_count": 0,
            }
        )
        sparse["insights"] = {
            "identity_score": 0,
            "plan_playlists": 0,
            "top_playlists": [],
            "coverage_ratio": 0.0,
            "collection_shape": "Just getting started",
            "pending_momentum": "No pending momentum",
        }
        sparse["plan_diagnostics"] = {"status": "skipped_missing_plan"}
        sparse["artifact_presence"] = {
            "config": True,
            "state": False,
            "managed_playlists": False,
            "liked_songs": False,
            "new_likes": False,
            "playlist_plan": False,
            "new_plan": False,
            "missing_matches": False,
        }
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.show_stats(sparse)
        output = capture.getvalue()
        self.assertIn("Identity score: 0/100", output)
        self.assertIn("Setup in progress", output)
        self.assertNotIn("Processed likes: 0", output)
        self.assertNotIn("Managed playlists: 0", output)
        self.assertIn("Health: Needs plan file", output)
        self.assertNotIn("Missing artifacts:", output)
        self.assertNotIn("Warnings:", output)
        self.assertIn("Diagnostics:", output)

    def test_replay_completed_step_renders_numbered_done_entry_in_plain_mode(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.start_flow(steps=["Auth check", "Export full liked songs"])
            ui.replay_completed_step("Auth check already completed")
        self.assertIn("Step 1/2 done | Auth check already completed", capture.getvalue())

    def test_style_paths_marks_paths_in_rich_mode_and_leaves_plain_text_unchanged(self) -> None:
        with patch("ytmusic_organizer.ui.Console"):
            ui_rich = WizardUI(enabled=True, force_tty=True)
            styled = ui_rich._style_paths(
                "Workspace /tmp/ws and prompt ~/data/full_reset_prompt_filled.txt and https://example.com/docs"
            )
        self.assertIn(f"[{ui_rich._COLOR_PATH}]/tmp/ws[/]", styled)
        self.assertIn(f"[{ui_rich._COLOR_PATH}]~/data/full_reset_prompt_filled.txt[/]", styled)
        self.assertIn("https://example.com/docs", styled)

        ui_plain = WizardUI(enabled=True, force_tty=False)
        plain = "Workspace /tmp/ws and prompt ~/data/full_reset_prompt_filled.txt"
        self.assertEqual(ui_plain._style_paths(plain), plain)

    def test_rich_outputs_apply_path_style_in_detail_callout_and_recap(self) -> None:
        with patch("ytmusic_organizer.ui.Console") as console_cls:
            console = console_cls.return_value
            ui = WizardUI(enabled=True, force_tty=True)
            ui.step_detail("Open prompt file: /tmp/ws/data/full_reset_prompt_filled.txt")
            detail_line = console.print.call_args_list[-1].args[0]
            self.assertIn(
                f"[{ui._COLOR_PATH}]/tmp/ws/data/full_reset_prompt_filled.txt[/]",
                detail_line,
            )

            ui.render_callout(
                "info",
                "Manual classification required",
                ["Open prompt file: /tmp/ws/data/full_reset_prompt_filled.txt"],
            )
            callout_panel = console.print.call_args_list[-1].args[0]
            self.assertIn(
                f"[{ui._COLOR_PATH}]/tmp/ws/data/full_reset_prompt_filled.txt[/]",
                callout_panel.renderable,
            )

            ui.render_recap("Setup Complete", {"workspace": "/tmp/ws"})
            recap_panel = console.print.call_args_list[-1].args[0]
            recap_table = recap_panel.renderable
            self.assertIn(f"[{ui._COLOR_PATH}]/tmp/ws[/]", recap_table.columns[1]._cells[0])

    def test_show_stats_treats_identity_zero_as_sparse_even_with_liked_snapshot(self) -> None:
        sparse = self._sample_result()
        sparse.update(
            {
                "processed_likes": 0,
                "managed_playlists": 0,
                "new_likes_pending": 0,
                "liked_snapshot_count": 338,
            }
        )
        sparse["insights"] = {
            "identity_score": 0,
            "plan_playlists": 0,
            "top_playlists": [],
            "coverage_ratio": 0.0,
            "collection_shape": "Growing catalog",
            "pending_momentum": "No pending momentum",
        }
        sparse["plan_diagnostics"] = {"status": "skipped_missing_plan"}
        sparse["artifact_presence"] = {
            "config": True,
            "state": False,
            "managed_playlists": False,
            "liked_songs": True,
            "new_likes": False,
            "playlist_plan": False,
            "new_plan": False,
            "missing_matches": True,
        }
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.show_stats(sparse)
        output = capture.getvalue()
        self.assertIn("Setup in progress", output)
        self.assertNotIn("Narrative: Your vibe is loading.", output)
        self.assertNotIn("Managed playlists: 0", output)
        self.assertNotIn("Processed likes: 0", output)
        self.assertNotIn("New likes pending: 0", output)


if __name__ == "__main__":
    unittest.main()
