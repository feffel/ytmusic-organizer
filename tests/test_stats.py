import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from ytmusic_organizer.workflows import run_stats


class StatsTests(unittest.TestCase):
    def test_run_stats_empty_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = run_stats(workspace)
            self.assertEqual(result["processed_likes"], 0)
            self.assertEqual(result["managed_playlists"], 0)
            self.assertEqual(result["missing_matches"], 0)
            self.assertEqual(result["new_likes_pending"], 0)
            self.assertEqual(result["liked_snapshot_count"], 0)
            self.assertFalse(result["artifact_presence"]["state"])
            self.assertEqual(result["plan_diagnostics"]["status"], "skipped_missing_plan")
            self.assertEqual(result["warnings"], [])
            self.assertFalse(workspace.exists())

    def test_run_stats_partial_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir(parents=True)
            (workspace / "state.json").write_text(
                json.dumps({"processed_video_ids": ["a", "b"]}),
                encoding="utf-8",
            )
            result = run_stats(workspace)
            self.assertEqual(result["processed_likes"], 2)
            self.assertEqual(result["managed_playlists"], 0)
            self.assertTrue(result["artifact_presence"]["state"])
            self.assertFalse(result["artifact_presence"]["managed_playlists"])
            self.assertEqual(result["plan_diagnostics"]["status"], "skipped_missing_plan")

    def test_run_stats_populated_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True)
            (workspace / "state.json").write_text(
                json.dumps({"processed_video_ids": ["a", "b", "c"]}),
                encoding="utf-8",
            )
            (workspace / "managed_playlists.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "playlists": [
                            {"name": "A", "playlist_id": "1"},
                            {"name": "B", "playlist_id": "2"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (data_dir / "missing_matches.json").write_text(
                json.dumps([{"song": "x"}]), encoding="utf-8"
            )
            (data_dir / "new_likes.json").write_text(
                json.dumps([{"video_id": "n1"}]), encoding="utf-8"
            )
            (data_dir / "liked_songs.json").write_text(
                json.dumps([{"video_id": "a"}, {"video_id": "b"}]),
                encoding="utf-8",
            )
            result = run_stats(workspace)
            self.assertEqual(result["processed_likes"], 3)
            self.assertEqual(result["managed_playlists"], 2)
            self.assertEqual(result["missing_matches"], 1)
            self.assertEqual(result["new_likes_pending"], 1)
            self.assertEqual(result["liked_snapshot_count"], 2)
            self.assertEqual(result["plan_diagnostics"]["status"], "skipped_missing_plan")
            self.assertIn("insights", result)
            self.assertEqual(result["insights"]["identity_score"], 0)
            self.assertEqual(result["insights"]["top_playlists"], [])

    def test_run_stats_valid_plan_diagnostics_with_default_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True)
            (workspace / "state.json").write_text(
                json.dumps({"processed_video_ids": ["vid-1"]}),
                encoding="utf-8",
            )
            (data_dir / "liked_songs.json").write_text(
                json.dumps(
                    [
                        {
                            "videoId": "vid-1",
                            "title": "Song A",
                            "artists": ["Artist A"],
                            "album": "",
                            "duration": "",
                        },
                        {
                            "videoId": "vid-2",
                            "title": "Song B",
                            "artists": ["Artist B"],
                            "album": "",
                            "duration": "",
                        },
                    ]
                ),
                encoding="utf-8",
            )
            (data_dir / "playlist_plan.json").write_text(
                json.dumps(
                    {
                        "playlists": [
                            {"name": "Chill", "songs": [{"title": "Song A", "artist": "Artist A"}]}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_stats(workspace)
            self.assertEqual(result["plan_diagnostics"]["status"], "ok")
            self.assertEqual(result["plan_diagnostics"]["matched"], 1)
            self.assertEqual(result["plan_diagnostics"]["missing"], 0)
            self.assertEqual(result["plan_diagnostics"]["loose"], 0)
            self.assertEqual(result["plan_diagnostics"]["ambiguous"], 0)
            self.assertIn("insights", result)
            self.assertEqual(result["insights"]["plan_playlists"], 1)
            self.assertEqual(result["insights"]["coverage_ratio"], 0.5)
            self.assertEqual(result["missing_required_artifacts"], ["config", "managed_playlists"])
            self.assertEqual(
                result["artifact_paths"]["missing_matches"], str(data_dir / "missing_matches.json")
            )

    def test_run_stats_setup_health_ignores_missing_sync_cycle_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True)
            (workspace / "config.toml").write_text(
                'classification_mode = "manual"\n', encoding="utf-8"
            )
            (workspace / "state.json").write_text(
                json.dumps({"processed_video_ids": ["vid-1"]}),
                encoding="utf-8",
            )
            (workspace / "managed_playlists.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "playlists": [
                            {"name": "Night Drive", "playlist_id": "pl-1"},
                            {"name": "Soft Focus", "playlist_id": "pl-2"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (data_dir / "liked_songs.json").write_text(
                json.dumps(
                    [
                        {
                            "videoId": "vid-1",
                            "title": "Song A",
                            "artists": ["Artist A"],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (data_dir / "playlist_plan.json").write_text(
                json.dumps(
                    {
                        "playlists": [
                            {
                                "name": "Night Drive",
                                "description": "Late-night synth and neon energy",
                                "songs": [
                                    {"title": "Song A", "artist": "Artist A"},
                                    {"title": "Song B", "artist": "Artist B"},
                                    {"title": "Song C", "artist": "Artist B"},
                                    {"title": "Song D", "artist": "Artist C"},
                                    {"title": "Song E", "artist": "Artist C"},
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_stats(workspace)

            self.assertFalse(result["artifact_presence"]["new_likes"])
            self.assertFalse(result["artifact_presence"]["new_plan"])
            self.assertEqual(result["missing_required_artifacts"], [])
            self.assertEqual(result["managed_playlist_names"], ["Night Drive", "Soft Focus"])
            self.assertEqual(result["plan_diagnostics"]["status"], "ok")
            self.assertEqual(
                result["insights"]["top_playlists"][0],
                {
                    "name": "Night Drive",
                    "songs": 5,
                    "description": "Late-night synth and neon energy",
                    "sample_songs": [
                        "Song A - Artist A",
                        "Song B - Artist B",
                        "Song C - Artist B",
                    ],
                    "top_artist": "Artist B (2 tracks)",
                    "runner_up_artist": "Artist C (2 tracks)",
                },
            )

    def test_run_stats_with_custom_plan_missing_liked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True)
            custom_plan = data_dir / "custom-plan.json"
            custom_plan.write_text(
                json.dumps(
                    {
                        "playlists": [
                            {"name": "Chill", "songs": [{"title": "Song A", "artist": "Artist A"}]}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_stats(workspace, plan_path=custom_plan)
            self.assertEqual(result["plan_diagnostics"]["status"], "skipped_missing_liked")
            self.assertEqual(result["warnings"], [])

    def test_run_stats_invalid_plan_schema_sets_invalid_plan_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True)
            (data_dir / "liked_songs.json").write_text(
                json.dumps(
                    [
                        {
                            "videoId": "vid-1",
                            "title": "Song A",
                            "artists": ["Artist A"],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (data_dir / "playlist_plan.json").write_text(json.dumps({"bad": []}), encoding="utf-8")

            result = run_stats(workspace)
            self.assertEqual(result["plan_diagnostics"]["status"], "invalid_plan")
            self.assertGreaterEqual(len(result["warnings"]), 1)

    def test_run_stats_invalid_liked_sets_invalid_liked_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True)
            (data_dir / "liked_songs.json").write_text("not json", encoding="utf-8")
            (data_dir / "playlist_plan.json").write_text(
                json.dumps(
                    {
                        "playlists": [
                            {"name": "Chill", "songs": [{"title": "Song A", "artist": "Artist A"}]}
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_stats(workspace)
            self.assertEqual(result["plan_diagnostics"]["status"], "invalid_liked")
            self.assertGreaterEqual(len(result["warnings"]), 1)

    def test_run_stats_malformed_artifacts_collect_warnings_without_failing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True)
            (workspace / "state.json").write_text("bad json", encoding="utf-8")
            (workspace / "managed_playlists.json").write_text("bad json", encoding="utf-8")
            (data_dir / "new_likes.json").write_text("bad json", encoding="utf-8")
            (data_dir / "missing_matches.json").write_text("bad json", encoding="utf-8")

            result = run_stats(workspace)
            self.assertEqual(result["processed_likes"], 0)
            self.assertEqual(result["managed_playlists"], 0)
            self.assertEqual(result["new_likes_pending"], 0)
            self.assertEqual(result["missing_matches"], 0)
            self.assertGreaterEqual(len(result["warnings"]), 4)

    def test_cli_stats_json_output_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "stats",
                    "--workspace",
                    str(workspace),
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["command"], "stats")
            self.assertIn("processed_likes", payload["result"])
            self.assertIn("artifact_presence", payload["result"])
            self.assertIn("plan_diagnostics", payload["result"])
            self.assertIn("warnings", payload["result"])


if __name__ == "__main__":
    unittest.main()
