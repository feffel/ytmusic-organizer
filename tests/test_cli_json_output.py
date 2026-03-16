import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


class CliJsonOutputTests(unittest.TestCase):
    def test_cleanup_dry_run_json_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "cleanup",
                    "--workspace",
                    str(workspace),
                    "--dry-run",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["command"], "cleanup")
            self.assertTrue(payload["result"]["dry_run"])
            self.assertIn("would_delete_playlists", payload["result"])
            self.assertIn("would_remove_local_files", payload["result"])
            self.assertIn("local_only", payload["result"])

    def test_cleanup_local_only_json_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "cleanup",
                    "--workspace",
                    str(workspace),
                    "--local-only",
                    "--yes",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["command"], "cleanup")
            self.assertIn("removed_local_files", payload["result"])

    def test_rebuild_dry_run_json_skips_yes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "rebuild",
                    "--workspace",
                    str(workspace),
                    "--mode",
                    "manual",
                    "--non-interactive",
                    "--dry-run",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
                input='{"playlists": []}\n',
            )
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["command"], "rebuild")
            self.assertNotIn("--yes is required", payload["error"])

    def test_setup_json_error_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            missing_auth = Path(tmp) / "missing-browser.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "setup",
                    "--workspace",
                    str(workspace),
                    "--non-interactive",
                    "--auth-file",
                    str(missing_auth),
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["command"], "setup")
            self.assertIn("Auth file is missing", payload["error"])

    def test_stats_missing_default_plan_returns_ok_with_diagnostics(self) -> None:
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
            self.assertEqual(result.returncode, 0)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["command"], "stats")
            self.assertEqual(payload["result"]["plan_diagnostics"]["status"], "skipped_missing_plan")
            self.assertIn("warnings", payload["result"])

    def test_stats_missing_liked_snapshot_returns_ok_with_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            plan_path = data_dir / "custom-plan.json"
            plan_path.write_text(
                json.dumps(
                    {"playlists": [{"name": "Chill", "songs": [{"title": "Song A", "artist": "Artist A"}]}]}
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "stats",
                    "--workspace",
                    str(workspace),
                    "--plan",
                    str(plan_path),
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["command"], "stats")
            self.assertEqual(payload["result"]["plan_diagnostics"]["status"], "skipped_missing_liked")

    def test_stats_success_returns_diagnostics_and_does_not_rewrite_missing_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True, exist_ok=True)

            liked_path = data_dir / "liked_songs.json"
            liked_path.write_text(
                json.dumps(
                    [
                        {
                            "videoId": "vid-1",
                            "title": "Song A",
                            "artists": ["Artist A"],
                            "album": "",
                            "duration": "",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            plan_path = data_dir / "playlist_plan.json"
            plan_path.write_text(
                json.dumps(
                    {"playlists": [{"name": "Chill", "songs": [{"title": "Song A", "artist": "Artist A"}]}]}
                ),
                encoding="utf-8",
            )
            missing_matches = data_dir / "missing_matches.json"
            original_missing = [{"playlist": "Existing", "title": "Keep", "artist": "Same"}]
            missing_matches.write_text(json.dumps(original_missing), encoding="utf-8")

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
            self.assertEqual(payload["result"]["plan_diagnostics"]["status"], "ok")
            self.assertEqual(payload["result"]["plan_diagnostics"]["matched"], 1)
            self.assertEqual(payload["result"]["plan_diagnostics"]["missing"], 0)
            self.assertEqual(payload["result"]["plan_diagnostics"]["loose"], 0)
            self.assertEqual(payload["result"]["plan_diagnostics"]["ambiguous"], 0)
            self.assertTrue(missing_matches.exists())
            self.assertEqual(json.loads(missing_matches.read_text(encoding="utf-8")), original_missing)


if __name__ == "__main__":
    unittest.main()
