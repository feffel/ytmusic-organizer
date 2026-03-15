import unittest

from ytmusic_organizer.validation import validate_full_plan, validate_new_plan


class ValidationTests(unittest.TestCase):
    def test_validate_full_plan_accepts_valid_shape(self) -> None:
        plan = {
            "strategy_options": [{"name": "A", "description": "B"}],
            "recommended_strategy": "A",
            "playlists": [{"name": "P", "songs": [{"title": "T", "artist": "A"}]}],
        }
        validate_full_plan(plan)

    def test_validate_new_plan_rejects_bad_shape(self) -> None:
        bad = {"playlists": [{"name": "P", "songs": [{"title": "T"}]}]}
        with self.assertRaises(ValueError) as ctx:
            validate_new_plan(bad)
        self.assertIn("artist", str(ctx.exception))

    def test_validate_full_plan_accepts_playlist_description(self) -> None:
        plan = {
            "playlists": [
                {
                    "name": "Night Drive",
                    "description": "Late-night synth and neon mood",
                    "songs": [{"title": "T", "artist": "A"}],
                }
            ]
        }
        validate_full_plan(plan)


if __name__ == "__main__":
    unittest.main()
