import tempfile
from pathlib import Path
import unittest

from ytmusic_organizer.auth_capture import (
    BrowserAuthCaptureError,
    capture_browser_auth_headers,
    redact_auth_secrets,
)


class _FakeRequest:
    def __init__(self, url: str, headers: dict[str, str]) -> None:
        self.url = url
        self._headers = headers

    def all_headers(self) -> dict[str, str]:
        return self._headers


class _FakePage:
    def __init__(self, context: "_FakeContext") -> None:
        self._context = context

    def goto(self, _url: str, wait_until: str = "domcontentloaded") -> None:  # noqa: ARG002
        self._context.emit_request()

    def wait_for_timeout(self, _milliseconds: int) -> None:
        return None


class _FakeContext:
    def __init__(self, request: _FakeRequest | None) -> None:
        self.pages: list[_FakePage] = []
        self._request = request
        self._handlers: dict[str, object] = {}
        self.closed = False

    def on(self, event_name: str, handler) -> None:  # noqa: ANN001
        self._handlers[event_name] = handler

    def new_page(self) -> _FakePage:
        page = _FakePage(self)
        self.pages.append(page)
        return page

    def emit_request(self) -> None:
        if self._request and "request" in self._handlers:
            self._handlers["request"](self._request)  # type: ignore[index,operator]

    def close(self) -> None:
        self.closed = True


class _FakeChromium:
    def __init__(self, context: _FakeContext) -> None:
        self.context = context
        self.profile_dir: str | None = None

    def launch_persistent_context(self, user_data_dir: str, **_kwargs):  # noqa: ANN001
        self.profile_dir = user_data_dir
        return self.context


class _FakePlaywright:
    def __init__(self, context: _FakeContext) -> None:
        self.chromium = _FakeChromium(context)


class _FakePlaywrightFactory:
    def __init__(self, context: _FakeContext) -> None:
        self.playwright = _FakePlaywright(context)

    def __call__(self):
        return self

    def __enter__(self) -> _FakePlaywright:
        return self.playwright

    def __exit__(self, *_exc) -> None:  # noqa: ANN002
        return None


class BrowserAuthCaptureTests(unittest.TestCase):
    def test_capture_returns_required_browser_headers_from_browse_request(self) -> None:
        request = _FakeRequest(
            "https://music.youtube.com/youtubei/v1/browse?alt=json",
            {
                "cookie": "__Secure-3PAPISID=sapisid; other=value",
                "authorization": "SAPISIDHASH 123_hash",
                "x-goog-authuser": "0",
                "origin": "https://music.youtube.com",
                "sec-fetch-site": "same-origin",
            },
        )
        context = _FakeContext(request)
        factory = _FakePlaywrightFactory(context)

        with tempfile.TemporaryDirectory() as tmp:
            headers = capture_browser_auth_headers(
                workspace=Path(tmp),
                timeout_seconds=1,
                playwright_factory=factory,
            )

        self.assertIn("cookie: __Secure-3PAPISID=sapisid; other=value", headers)
        self.assertIn("authorization: SAPISIDHASH 123_hash", headers)
        self.assertIn("x-goog-authuser: 0", headers)
        self.assertIn("origin: https://music.youtube.com", headers)
        self.assertNotIn("sec-fetch-site", headers)
        self.assertTrue(context.closed)
        self.assertTrue(factory.playwright.chromium.profile_dir.endswith("browser-auth-profile"))

    def test_capture_times_out_without_leaking_seen_header_values(self) -> None:
        request = _FakeRequest(
            "https://music.youtube.com/youtubei/v1/browse?alt=json",
            {
                "cookie": "__Secure-3PAPISID=secret-cookie",
                "x-goog-authuser": "0",
            },
        )
        context = _FakeContext(request)

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(BrowserAuthCaptureError) as ctx:
                capture_browser_auth_headers(
                    workspace=Path(tmp),
                    timeout_seconds=0,
                    playwright_factory=_FakePlaywrightFactory(context),
                )

        message = str(ctx.exception)
        self.assertIn("Timed out waiting for authenticated YouTube Music traffic", message)
        self.assertNotIn("secret-cookie", message)

    def test_redact_auth_secrets_removes_cookie_and_authorization_values(self) -> None:
        message = (
            "capture failed: cookie=__Secure-3PAPISID=secret authorization=SAPISIDHASH 123_hash"
        )

        redacted = redact_auth_secrets(message)

        self.assertNotIn("secret", redacted)
        self.assertNotIn("123_hash", redacted)
        self.assertIn("<redacted>", redacted)


if __name__ == "__main__":
    unittest.main()
