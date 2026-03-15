import tempfile
from pathlib import Path
import unittest

from ytmusic_organizer.workflows import cleanup_local_artifacts


class CleanupTests(unittest.TestCase):
    def test_cleanup_local_artifacts_removes_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = [
                root / "state.json",
                root / "managed_playlists.json",
                root / "bootstrap.json",
                root / "setup_state.json",
                root / "data" / "liked_songs.json",
                root / "data" / "new_likes.json",
            ]
            for f in files:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("{}", encoding="utf-8")

            removed = cleanup_local_artifacts(root)
            self.assertGreaterEqual(removed, len(files))
            for f in files:
                self.assertFalse(f.exists())


if __name__ == "__main__":
    unittest.main()
