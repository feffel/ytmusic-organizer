import unittest

from ytmusic_organizer.matching import artist_match, find_match, normalize, title_match


class MatchingTests(unittest.TestCase):
    def test_normalize_removes_noise(self) -> None:
        self.assertEqual(normalize("Song Title (Live) feat. Person"), "song title")

    def test_title_match_handles_containment(self) -> None:
        self.assertTrue(title_match("Houdini", "Houdini - Live"))

    def test_artist_match_handles_partials(self) -> None:
        self.assertTrue(artist_match("Eminem", ["Eminem", "Rihanna"]))

    def test_find_match_exact(self) -> None:
        liked = [{"title": "Houdini", "artists": ["Eminem"], "videoId": "abc"}]
        song = {"title": "Houdini", "artist": "Eminem"}
        match, match_type = find_match(song, liked)
        self.assertEqual(match["videoId"], "abc")
        self.assertEqual(match_type, "exact")


if __name__ == "__main__":
    unittest.main()
