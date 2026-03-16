import io
import unittest
from unittest.mock import patch

from ytmusic_organizer.planning import read_json_from_stdin


class _SequencedStdin:
    def __init__(self, chunks: list[str], interactive: bool):
        self._chunks = chunks
        self._interactive = interactive

    def read(self) -> str:
        if self._chunks:
            return self._chunks.pop(0)
        return ""

    def isatty(self) -> bool:
        return self._interactive


class ManualStdinTests(unittest.TestCase):
    def test_read_json_from_stdin_parses_valid_json(self) -> None:
        fake = _SequencedStdin(['{"playlists": []}'], interactive=False)
        with patch("sys.stdin", fake):
            value = read_json_from_stdin()
        self.assertEqual(value, {"playlists": []})

    def test_read_json_from_stdin_raises_for_invalid_non_interactive_input(self) -> None:
        fake = _SequencedStdin(["not json"], interactive=False)
        with patch("sys.stdin", fake):
            with self.assertRaises(ValueError) as ctx:
                read_json_from_stdin()
        self.assertIn("Invalid JSON from stdin", str(ctx.exception))

    def test_read_json_from_stdin_reprompts_until_valid_for_interactive_input(self) -> None:
        fake = _SequencedStdin(["nope", '{"playlists": []}'], interactive=True)
        with patch("sys.stdin", fake), patch("sys.stdout", new_callable=io.StringIO):
            value = read_json_from_stdin()
        self.assertEqual(value, {"playlists": []})


if __name__ == "__main__":
    unittest.main()
