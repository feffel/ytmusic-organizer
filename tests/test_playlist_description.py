import unittest

from ytmusic_organizer.ytmusic_ops import build_playlist_description


class PlaylistDescriptionTests(unittest.TestCase):
    def test_uses_playlist_description_and_managed_tag(self) -> None:
        playlist = {"name": "Night Drive", "description": "Late-night synth and neon energy"}
        value = build_playlist_description(playlist)
        self.assertIn("Late-night synth and neon energy", value)
        self.assertIn("Managed by ytmusic-organizer", value)

    def test_generates_default_vibe_when_missing(self) -> None:
        playlist = {"name": "Arabic Chill"}
        value = build_playlist_description(playlist)
        self.assertIn("Vibe:", value)
        self.assertIn("Arabic Chill", value)
        self.assertIn("Managed by ytmusic-organizer", value)


if __name__ == "__main__":
    unittest.main()
