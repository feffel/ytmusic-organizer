import unittest
from unittest.mock import patch

from ytmusic_organizer.workflows import (
    _collect_auth_headers_from_line_reader,
    _collect_auth_headers_from_stdin,
    _normalize_auth_headers,
)


def _reader_from_lines(lines: list[str]):
    iterator = iter(lines)

    def _next_line() -> str:
        try:
            return next(iterator)
        except StopIteration as exc:
            raise EOFError from exc

    return _next_line


class AuthHeaderNormalizationTests(unittest.TestCase):
    def test_accepts_raw_header_lines(self) -> None:
        raw = "\n".join(
            [
                "cookie: a=b; c=d",
                "x-goog-authuser: 1",
                "x-origin: https://music.youtube.com",
            ]
        )
        normalized = _normalize_auth_headers(raw)
        self.assertIn("cookie: a=b; c=d", normalized)
        self.assertIn("x-goog-authuser: 1", normalized)
        self.assertIn("x-origin: https://music.youtube.com", normalized)

    def test_accepts_json_style_headers(self) -> None:
        raw = """{
  "cookie": "a=b; c=d",
  "x-goog-authuser": "1",
  "x-origin": "https://music.youtube.com"
}"""
        normalized = _normalize_auth_headers(raw)
        self.assertIn("cookie: a=b; c=d", normalized)
        self.assertIn("x-goog-authuser: 1", normalized)
        self.assertIn("x-origin: https://music.youtube.com", normalized)

    def test_rejects_missing_cookie(self) -> None:
        raw = "x-goog-authuser: 1"
        with self.assertRaises(RuntimeError) as ctx:
            _normalize_auth_headers(raw)
        self.assertIn(
            "AUTH_HEADERS_INVALID::Missing required header(s): cookie", str(ctx.exception)
        )

    def test_rejects_missing_authuser(self) -> None:
        raw = "cookie: a=b"
        with self.assertRaises(RuntimeError) as ctx:
            _normalize_auth_headers(raw)
        self.assertIn(
            "AUTH_HEADERS_INVALID::Missing required header(s): x-goog-authuser", str(ctx.exception)
        )

    def test_handles_quotes_and_trailing_commas(self) -> None:
        raw = "\n".join(
            [
                '"cookie": "a=b; c=d",',
                '"x-goog-authuser": "1",',
            ]
        )
        normalized = _normalize_auth_headers(raw)
        self.assertIn("cookie: a=b; c=d", normalized)
        self.assertIn("x-goog-authuser: 1", normalized)

    def test_line_reader_raw_headers_complete_on_blank_line(self) -> None:
        line_reader = _reader_from_lines(
            [
                "cookie: a=b",
                "x-goog-authuser: 1",
                "",
            ]
        )
        normalized = _collect_auth_headers_from_line_reader(line_reader)
        self.assertIn("cookie: a=b", normalized)
        self.assertIn("x-goog-authuser: 1", normalized)

    def test_line_reader_json_autocompletes_on_closing_brace(self) -> None:
        line_reader = _reader_from_lines(
            [
                "{",
                '  "cookie": "a=b",',
                '  "x-goog-authuser": "1"',
                "}",
            ]
        )
        normalized = _collect_auth_headers_from_line_reader(line_reader)
        self.assertIn("cookie: a=b", normalized)
        self.assertIn("x-goog-authuser: 1", normalized)

    def test_line_reader_incomplete_json_on_eof_raises(self) -> None:
        line_reader = _reader_from_lines(
            [
                "{",
                '  "cookie": "a=b",',
            ]
        )
        with self.assertRaises(RuntimeError) as ctx:
            _collect_auth_headers_from_line_reader(line_reader)
        self.assertIn(
            "AUTH_HEADERS_INVALID::Headers JSON is incomplete or malformed.", str(ctx.exception)
        )

    def test_collector_json_autocompletes_without_eof(self) -> None:
        lines = iter(
            [
                "{",
                '  "cookie": "a=b",',
                '  "x-goog-authuser": "1"',
                "}",
            ]
        )

        def fake_input(prompt: str = "") -> str:  # noqa: ARG001
            value = next(lines)
            return value

        with patch("builtins.input", side_effect=fake_input):
            normalized = _collect_auth_headers_from_stdin(ui=None)
        self.assertIn("cookie: a=b", normalized)
        self.assertIn("x-goog-authuser: 1", normalized)

    def test_collector_raw_headers_complete_on_blank_line(self) -> None:
        lines = iter(
            [
                "cookie: a=b",
                "x-goog-authuser: 1",
                "",
            ]
        )

        def fake_input(prompt: str = "") -> str:  # noqa: ARG001
            value = next(lines)
            return value

        with patch("builtins.input", side_effect=fake_input):
            normalized = _collect_auth_headers_from_stdin(ui=None)
        self.assertIn("cookie: a=b", normalized)
        self.assertIn("x-goog-authuser: 1", normalized)

    def test_collector_incomplete_json_raises_actionable_error(self) -> None:
        lines = iter(
            [
                "{",
                '  "cookie": "a=b",',
            ]
        )

        def fake_input(prompt: str = "") -> str:  # noqa: ARG001
            try:
                return next(lines)
            except StopIteration as exc:
                raise EOFError from exc

        with patch("builtins.input", side_effect=fake_input):
            with self.assertRaises(RuntimeError) as ctx:
                _collect_auth_headers_from_stdin(ui=None)
        self.assertIn(
            "AUTH_HEADERS_INVALID::Headers JSON is incomplete or malformed.", str(ctx.exception)
        )

    def test_collector_accepts_very_long_cookie_line(self) -> None:
        cookie_value = "x" * 12000
        lines = iter(
            [
                f"cookie: {cookie_value}",
                "x-goog-authuser: 1",
                "",
            ]
        )

        def fake_input(prompt: str = "") -> str:  # noqa: ARG001
            value = next(lines)
            return value

        with patch("builtins.input", side_effect=fake_input):
            normalized = _collect_auth_headers_from_stdin(ui=None)
        self.assertIn(f"cookie: {cookie_value}", normalized)
        self.assertIn("x-goog-authuser: 1", normalized)


if __name__ == "__main__":
    unittest.main()
