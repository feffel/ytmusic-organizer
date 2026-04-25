from __future__ import annotations

import io
import os
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
            "plan_diagnostics": {
                "status": "ok",
                "matched": 60,
                "missing": 3,
                "loose": 2,
                "ambiguous": 1,
            },
            "insights": {
                "identity_score": 92,
                "plan_playlists": 7,
                "top_playlists": [
                    {
                        "name": "Night Drive",
                        "songs": 18,
                        "description": "Late-night synth and neon energy",
                        "top_artist": "Artist A (2 tracks)",
                        "runner_up_artist": "Artist B (1 track)",
                        "sample_songs": [
                            "Song A - Artist A",
                            "Song B - Artist B",
                            "Song C - Artist C",
                        ],
                    },
                    {
                        "name": "Soft Focus",
                        "songs": 12,
                        "description": "Quiet songs for concentration",
                        "top_artist": "Artist D (1 track)",
                        "sample_songs": ["Song D - Artist D"],
                    },
                    {
                        "name": "Gym",
                        "songs": 9,
                        "sample_songs": [],
                    },
                ],
                "coverage_ratio": 0.82,
                "collection_shape": "Growing catalog",
                "pending_momentum": "Steady momentum",
            },
            "artifact_paths": {
                "missing_matches": "/tmp/ws/data/missing_matches.json",
            },
            "missing_required_artifacts": [],
            "managed_playlist_names": [
                "Night Drive",
                "Soft Focus",
                "Gym",
                "Sunday",
            ],
            "warnings": [],
        }

    def _long_text_result(self) -> dict:
        result = self._sample_result()
        result["insights"]["top_playlists"] = [
            {
                "name": "Arabic Pop / Mainstream / Levant Favorites",
                "songs": 31,
                "description": "Mainstream Arabic pop, nostalgic radio hits, and polished Levant hooks",
                "top_artist": "Fairuz (8 tracks)",
                "runner_up_artist": "Amr Diab (6 tracks)",
                "sample_songs": ["Habibi - Artist One", "Yalla - Artist Two"],
            },
            {
                "name": "Covers / Comedy / Internet Deep Cuts",
                "songs": 28,
                "description": "Arabic rap, trap, mahraganat, internet jokes, and viral oddities",
                "top_artist": "Wegz (5 tracks)",
                "runner_up_artist": "Marwan Pablo (4 tracks)",
                "sample_songs": ["Cover One - Artist Three"],
            },
            {
                "name": "Arabic Rap / Trap / Mahraganat Energy",
                "songs": 21,
                "description": "Covers, comedy, internet-era edits, and personality-heavy tracks",
                "top_artist": "El Joker (4 tracks)",
                "sample_songs": [],
            },
        ]
        result["managed_playlist_names"] = [
            "Arabic Pop / Mainstream / Levant Favorites",
            "Covers / Comedy / Internet Deep Cuts",
            "Arabic Rap / Trap / Mahraganat Energy",
            "Arabic Indie & Alternative",
            "Khaleeji & Heritage",
            "Afro / Amapiano / Global Groove",
            "Latin / Party Throwbacks",
            "House / EDM / Remixes",
            "Hip-Hop / R&B",
            "Rock / Alternative / Country",
            "Chill / Acoustic / Sad",
            "Motivation & Abundance",
        ]
        return result

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
            self.assertEqual(live.update.call_count, 3)
            self.assertEqual(sleep_mock.call_count, 3)
            self.assertEqual(sleep_mock.call_args_list[0].args[0], 0.25)
            self.assertEqual(sleep_mock.call_args_list[1].args[0], 0.18)
            self.assertEqual(sleep_mock.call_args_list[2].args[0], 0.18)

    def test_show_stats_plain_mode_uses_layout_sections(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.show_stats(self._sample_result())
        output = capture.getvalue()
        self.assertIn("Status Overview", output)
        self.assertIn("Plan & Coverage", output)
        self.assertIn("Playlist Standings", output)
        self.assertNotIn("Queue & Gaps", output)
        self.assertNotIn("Health Check", output)
        self.assertIn("Overall status: Healthy - ready for sharing", output)
        self.assertNotIn("Diagnostics:", output)
        self.assertNotIn("Narrative:", output)
        self.assertNotIn("Pending momentum:", output)

    def test_show_stats_plain_mode_shows_missing_match_path_and_playlist_detail(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.show_stats(self._sample_result())
        output = capture.getvalue()
        self.assertIn("Missing matches: 3", output)
        self.assertIn("View missing matches: /tmp/ws/data/missing_matches.json", output)
        self.assertIn("SILVER #2", output)
        self.assertIn("GOLD #1", output)
        self.assertIn("BRONZE #3", output)
        self.assertLess(output.index("GOLD #1"), output.index("SILVER #2"))
        self.assertLess(output.index("SILVER #2"), output.index("BRONZE #3"))
        self.assertIn("│ Soft Focus", output)
        self.assertIn("│ Night Drive", output)
        self.assertIn("│ Gym", output)
        self.assertIn("Late-night synth", output)
        self.assertIn("Artist A (2 tracks)", output)
        self.assertIn("Artist B (1 track)", output)
        self.assertNotIn("samples:", output.lower())
        self.assertNotIn("Honorable mentions", output)
        self.assertIn("Managed playlists: 4 total", output)
        self.assertIn("│ 1  │ Night Drive", output)
        self.assertIn("│ 4  │ Sunday", output)
        self.assertNotIn("████", output)
        self.assertNotIn("…", output)

    def test_stats_podium_wraps_long_text_and_honorable_mentions(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.show_stats(self._long_text_result())
        output = capture.getvalue()

        self.assertNotIn("…", output)
        self.assertNotIn("████", output)
        self.assertIn("Covers / Comedy / Internet", output)
        self.assertIn("Deep Cuts", output)
        self.assertIn("Arabic rap, trap,", output)
        self.assertIn("mahraganat", output)
        self.assertIn("Fairuz (8 tracks)", output)
        self.assertNotIn("Honorable mentions:", output)
        self.assertIn("Arabic Indie & Alternative", output)
        self.assertIn("Motivation & Abundance", output)
        managed_section = False
        for line in output.splitlines():
            if "Managed playlists: 12 total" in line:
                managed_section = True
            if managed_section and line.strip().startswith("│"):
                self.assertLessEqual(len(line), 88)

    def test_stats_unhealthy_output_collapses_diagnostics_into_status_overview(self) -> None:
        sparse = self._sample_result()
        sparse.update(
            {
                "processed_likes": 0,
                "managed_playlists": 0,
                "new_likes_pending": 0,
                "liked_snapshot_count": 0,
                "managed_playlist_names": [],
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
        sparse["missing_required_artifacts"] = [
            "state",
            "managed_playlists",
            "liked_songs",
            "playlist_plan",
        ]
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.show_stats(sparse)
        output = capture.getvalue()

        self.assertIn("Overall status: Needs plan file - run setup/rebuild", output)
        self.assertIn("Diagnostics: missing required state", output)
        self.assertNotIn("Health Check", output)

    def test_rich_stats_podium_uses_medal_colors(self) -> None:
        ui = WizardUI(enabled=True, force_tty=False)
        sections = ui._build_stats_sections(
            identity_score=92,
            sparse=False,
            collection_shape="Growing catalog",
            managed_playlists=4,
            managed_playlist_names=["Night Drive", "Soft Focus", "Gym", "Sunday"],
            processed_likes=120,
            plan_playlists=4,
            plan_status_raw="ok",
            plan_status="Ready",
            coverage_ratio=0.82,
            top_playlists=self._sample_result()["insights"]["top_playlists"],
            pending_likes=4,
            missing_matches=3,
            missing_matches_path="/tmp/ws/data/missing_matches.json",
            liked_snapshot=150,
            health_label="Healthy",
            health_note="ready for sharing",
            diagnostics_line=None,
        )

        rendered = ui._render_stats_canvas([sections[2]])

        self.assertIn("[bold #cfd6e6]SILVER #2", rendered)
        self.assertIn("[bold #ffd166]GOLD #1", rendered)
        self.assertIn("[bold #d08c60]BRONZE #3", rendered)

    def test_show_stats_sparse_mode_de_emphasizes_zeros(self) -> None:
        sparse = self._sample_result()
        sparse.update(
            {
                "processed_likes": 0,
                "managed_playlists": 0,
                "new_likes_pending": 0,
                "liked_snapshot_count": 0,
                "managed_playlist_names": [],
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
        self.assertNotIn("Processed likes: 0", output)
        self.assertNotIn("Managed playlists: 0", output)
        self.assertIn("Overall status: Needs plan file", output)
        self.assertNotIn("Missing artifacts:", output)
        self.assertNotIn("Warnings:", output)
        self.assertIn("Diagnostics:", output)
        self.assertNotIn("Narrative:", output)
        self.assertNotIn("Pending momentum:", output)

    def test_show_stats_does_not_mark_missing_sync_artifacts_as_needing_setup(self) -> None:
        result = self._sample_result()
        result["artifact_presence"] = {
            "config": True,
            "state": True,
            "managed_playlists": True,
            "liked_songs": True,
            "new_likes": False,
            "playlist_plan": True,
            "new_plan": False,
            "missing_matches": False,
        }
        result["missing_required_artifacts"] = []
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.show_stats(result)
        output = capture.getvalue()
        self.assertIn("Overall status: Healthy - ready for sharing", output)
        self.assertNotIn("Needs setup", output)

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

    def test_rich_callout_emphasizes_suggested_command_lines(self) -> None:
        with patch("ytmusic_organizer.ui.Console") as console_cls:
            console = console_cls.return_value
            ui = WizardUI(enabled=True, force_tty=True)
            ui.render_callout(
                "warning",
                "Setup interrupted",
                [
                    "How to fix:",
                    "1. Re-run setup:",
                    "   ytmo setup",
                ],
            )
            callout_panel = console.print.call_args_list[-1].args[0]
            self.assertIn(f"[{ui._COLOR_PATH}]ytmo setup[/]", callout_panel.renderable)

    def test_plain_callout_preserves_raw_command_lines(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.render_callout(
                "warning",
                "Setup interrupted",
                [
                    "How to fix:",
                    "1. Re-run setup:",
                    "   ytmo setup",
                ],
            )
        output = capture.getvalue()
        self.assertIn("  How to fix:", output)
        self.assertIn("  1. Re-run setup:", output)
        self.assertIn("     ytmo setup", output)
        self.assertNotIn("[warning]    ytmo setup", output)

    def test_show_stats_treats_identity_zero_as_sparse_even_with_liked_snapshot(self) -> None:
        sparse = self._sample_result()
        sparse.update(
            {
                "processed_likes": 0,
                "managed_playlists": 0,
                "new_likes_pending": 0,
                "liked_snapshot_count": 338,
                "managed_playlist_names": [],
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
        self.assertNotIn("Narrative: Your vibe is loading.", output)
        self.assertNotIn("Managed playlists: 0", output)
        self.assertNotIn("Processed likes: 0", output)
        self.assertNotIn("New likes pending: 0", output)

    def test_plain_mode_flow_markers_use_neon_stage_tags(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.command_header("ytmusic-organizer sync", "incremental update")
            ui.start_step("Export new likes")
            ui.step_detail("Scanning source workspace")
            ui.finish_step("Detected 2 new likes")
            ui.finish_flow("Sync completed")

        output = capture.getvalue()
        self.assertIn("[stage] ytmusic-organizer sync", output)
        self.assertIn("[beat] Step | Export new likes", output)
        self.assertIn("[note] Scanning source workspace", output)
        self.assertIn("[drop] done: Detected 2 new likes", output)
        self.assertIn("[encore] Flow complete: Sync completed", output)

    def test_microcopy_probability_defaults_to_twelve_percent(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            ui = WizardUI(enabled=True, force_tty=False)
        self.assertEqual(ui._microcopy_probability, 0.12)

    def test_warning_microcopy_is_additive_and_keeps_primary_line(self) -> None:
        capture = io.StringIO()
        with (
            patch("sys.stdout", capture),
            patch("ytmusic_organizer.ui.random.random", return_value=0.01),
            patch("ytmusic_organizer.ui.random.choice", return_value={"text": "SARC_LINE"}),
        ):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.render_callout("warning", "Caution", ["No changes were applied."])
        output = capture.getvalue()
        self.assertIn("No changes were applied.", output)
        self.assertIn("Caution", output)
        self.assertIn("SARC_LINE", output)

    def test_warning_microcopy_not_added_when_probability_misses(self) -> None:
        capture = io.StringIO()
        with (
            patch("sys.stdout", capture),
            patch("ytmusic_organizer.ui.random.random", return_value=0.99),
        ):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.render_callout("warning", "Caution", ["No changes were applied."])
        output = capture.getvalue()
        self.assertIn("No changes were applied.", output)
        self.assertNotIn("SARC_LINE", output)

    def test_error_callouts_do_not_receive_warning_suffix(self) -> None:
        capture = io.StringIO()
        with (
            patch("sys.stdout", capture),
            patch("ytmusic_organizer.ui.random.random", return_value=0.0),
        ):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.render_callout("error", "Error", ["Auth file is missing."])
        output = capture.getvalue()
        self.assertIn("Auth file is missing.", output)
        self.assertNotIn("SARC_LINE", output)

    def test_recap_can_append_optional_microcopy(self) -> None:
        capture = io.StringIO()
        with (
            patch("sys.stdout", capture),
            patch("ytmusic_organizer.ui.random.random", return_value=0.01),
            patch("ytmusic_organizer.ui.random.choice", return_value={"text": "SARC_LINE"}),
        ):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.render_recap("Sync Complete", {"new_likes": 3})
        output = capture.getvalue()
        self.assertIn("Sync Complete", output)
        self.assertIn("New Likes: 3", output)
        self.assertIn("SARC_LINE", output)

    def test_finish_step_can_append_optional_microcopy(self) -> None:
        capture = io.StringIO()
        with (
            patch("sys.stdout", capture),
            patch("ytmusic_organizer.ui.random.random", return_value=0.01),
            patch("ytmusic_organizer.ui.random.choice", return_value={"text": "SARC_LINE"}),
        ):
            ui = WizardUI(enabled=True, force_tty=False)
            ui.finish_step("Plan ready")
        output = capture.getvalue()
        self.assertIn("[drop] done: Plan ready", output)
        self.assertIn("SARC_LINE", output)


if __name__ == "__main__":
    unittest.main()
