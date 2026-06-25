import tempfile
from pathlib import Path
import unittest

from ytmusic_organizer.auth_capture import (
    BrowserAuthCaptureError,
    install_playwright_chromium,
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
    def __init__(self, context: "_FakeContext", fail_bring_to_front: bool = False) -> None:
        self._context = context
        self.bring_to_front_calls = 0
        self.fail_bring_to_front = fail_bring_to_front

    def bring_to_front(self) -> None:
        self.bring_to_front_calls += 1
        if self.fail_bring_to_front:
            raise RuntimeError("cannot focus page")

    def goto(self, _url: str, wait_until: str = "domcontentloaded") -> None:  # noqa: ARG002
        self._context.emit_request()

    def wait_for_timeout(self, _milliseconds: int) -> None:
        return None


class _FakePageWithoutBringToFront:
    def __init__(self, context: "_FakeContext") -> None:
        self._context = context

    def goto(self, _url: str, wait_until: str = "domcontentloaded") -> None:  # noqa: ARG002
        self._context.emit_request()

    def wait_for_timeout(self, _milliseconds: int) -> None:
        return None


class _FakeContext:
    def __init__(
        self,
        request: _FakeRequest | None,
        *,
        page_without_bring_to_front: bool = False,
        fail_bring_to_front: bool = False,
    ) -> None:
        self.pages: list[_FakePage] = []
        self._request = request
        self._handlers: dict[str, object] = {}
        self.closed = False
        self.page_without_bring_to_front = page_without_bring_to_front
        self.fail_bring_to_front = fail_bring_to_front

    def on(self, event_name: str, handler) -> None:  # noqa: ANN001
        self._handlers[event_name] = handler

    def new_page(self):
        page = (
            _FakePageWithoutBringToFront(self)
            if self.page_without_bring_to_front
            else _FakePage(self, fail_bring_to_front=self.fail_bring_to_front)
        )
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


class _MissingBrowserChromium:
    def launch_persistent_context(self, user_data_dir: str, **_kwargs):  # noqa: ANN001, ARG002
        raise RuntimeError("Executable doesn't exist at /tmp/chromium")


class _FakePlaywright:
    def __init__(self, context: _FakeContext) -> None:
        self.chromium = _FakeChromium(context)


class _MissingBrowserPlaywright:
    chromium = _MissingBrowserChromium()


class _FakePlaywrightFactory:
    def __init__(self, context: _FakeContext) -> None:
        self.playwright = _FakePlaywright(context)

    def __call__(self):
        return self

    def __enter__(self) -> _FakePlaywright:
        return self.playwright

    def __exit__(self, *_exc) -> None:  # noqa: ANN002
        return None


class _MissingBrowserFactory:
    def __call__(self):
        return self

    def __enter__(self) -> _MissingBrowserPlaywright:
        return _MissingBrowserPlaywright()

    def __exit__(self, *_exc) -> None:  # noqa: ANN002
        return None


class _CompletedProcess:
    returncode = 0
    stdout = "installed"
    stderr = ""


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
        self.assertEqual(context.pages[0].bring_to_front_calls, 2)

    def test_capture_ignores_unavailable_browser_foregrounding(self) -> None:
        request = _FakeRequest(
            "https://music.youtube.com/youtubei/v1/browse?alt=json",
            {
                "cookie": "__Secure-3PAPISID=sapisid",
                "authorization": "SAPISIDHASH 123_hash",
                "x-goog-authuser": "0",
            },
        )
        context = _FakeContext(request, fail_bring_to_front=True)

        with tempfile.TemporaryDirectory() as tmp:
            headers = capture_browser_auth_headers(
                workspace=Path(tmp),
                timeout_seconds=1,
                playwright_factory=_FakePlaywrightFactory(context),
            )

        self.assertIn("authorization: SAPISIDHASH 123_hash", headers)

    def test_capture_works_when_page_has_no_foregrounding_api(self) -> None:
        request = _FakeRequest(
            "https://music.youtube.com/youtubei/v1/browse?alt=json",
            {
                "cookie": "__Secure-3PAPISID=sapisid",
                "authorization": "SAPISIDHASH 123_hash",
                "x-goog-authuser": "0",
            },
        )
        context = _FakeContext(request, page_without_bring_to_front=True)

        with tempfile.TemporaryDirectory() as tmp:
            headers = capture_browser_auth_headers(
                workspace=Path(tmp),
                timeout_seconds=1,
                playwright_factory=_FakePlaywrightFactory(context),
            )

        self.assertIn("authorization: SAPISIDHASH 123_hash", headers)

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

    def test_missing_chromium_error_requests_automated_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(BrowserAuthCaptureError) as ctx:
                capture_browser_auth_headers(
                    workspace=Path(tmp),
                    playwright_factory=_MissingBrowserFactory(),
                )

        message = str(ctx.exception)
        self.assertIn("Automated browser support needs Chromium", message)
        self.assertNotIn("python -m playwright install chromium", message)

    def test_installer_uses_current_runtime_playwright_module(self) -> None:
        observed: dict[str, object] = {}

        def fake_run(command, **kwargs):  # noqa: ANN001
            observed["command"] = command
            observed["kwargs"] = kwargs
            return _CompletedProcess()

        install_playwright_chromium(run_command=fake_run)

        command = observed["command"]
        self.assertIsInstance(command, list)
        self.assertEqual(command[1:], ["-m", "playwright", "install", "chromium"])
        self.assertIn("capture_output", observed["kwargs"])
        self.assertTrue(observed["kwargs"]["capture_output"])  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
