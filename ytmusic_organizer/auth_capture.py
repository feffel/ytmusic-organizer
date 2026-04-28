from __future__ import annotations

from pathlib import Path
import re
import time
from typing import Any, Callable
from urllib.parse import urlparse


class BrowserAuthCaptureError(RuntimeError):
    """Raised when browser-assisted auth capture cannot produce usable headers."""


_SECRET_PATTERNS = (
    re.compile(r"(cookie\s*[:=]\s*)([^\n\r]+)", re.IGNORECASE),
    re.compile(r"(authorization\s*[:=]\s*)([^\n\r]+)", re.IGNORECASE),
)


def redact_auth_secrets(message: str) -> str:
    redacted = str(message)
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(r"\1<redacted>", redacted)
    return redacted


def _is_browse_request(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc == "music.youtube.com" and parsed.path == "/youtubei/v1/browse"


def _request_headers(request: Any) -> dict[str, str]:
    raw_headers = request.all_headers() if hasattr(request, "all_headers") else request.headers
    return {str(key).lower(): str(value) for key, value in dict(raw_headers).items()}


def _usable_browser_headers(headers: dict[str, str]) -> dict[str, str] | None:
    cookie = headers.get("cookie", "").strip()
    authorization = headers.get("authorization", "").strip()
    authuser = headers.get("x-goog-authuser", "").strip()
    origin = headers.get("origin", "").strip() or "https://music.youtube.com"

    if not cookie or not authorization or not authuser:
        return None
    if "SAPISIDHASH" not in authorization:
        return None

    return {
        "cookie": cookie,
        "authorization": authorization,
        "x-goog-authuser": authuser,
        "origin": origin,
    }


def _headers_to_raw(headers: dict[str, str]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in headers.items())


def _default_playwright_factory() -> Any:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - exercised through workflow fallback
        raise BrowserAuthCaptureError(
            "Playwright is not installed or is not available in this environment."
        ) from exc
    return sync_playwright()


def _browser_error_message(exc: Exception) -> str:
    message = redact_auth_secrets(str(exc))
    if "Executable doesn't exist" in message or "playwright install" in message:
        return (
            "Playwright Chromium is not installed. "
            "Run `pipx run playwright install chromium`, then retry setup."
        )
    return message


def capture_browser_auth_headers(
    workspace: Path,
    timeout_seconds: int = 180,
    playwright_factory: Callable[[], Any] | None = None,
) -> str:
    factory = playwright_factory or _default_playwright_factory
    profile_dir = workspace / "browser-auth-profile"
    captured: dict[str, str] | None = None

    try:
        with factory() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            try:

                def handle_request(request: Any) -> None:
                    nonlocal captured
                    if captured is not None:
                        return
                    if not _is_browse_request(str(request.url)):
                        return
                    headers = _usable_browser_headers(_request_headers(request))
                    if headers is not None:
                        captured = headers

                context.on("request", handle_request)
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://music.youtube.com", wait_until="domcontentloaded")

                deadline = time.monotonic() + timeout_seconds
                while captured is None and time.monotonic() < deadline:
                    page.wait_for_timeout(500)

                if captured is None:
                    raise BrowserAuthCaptureError(
                        "Timed out waiting for authenticated YouTube Music traffic. "
                        "Confirm the browser is logged in and reload music.youtube.com."
                    )

                return _headers_to_raw(captured)
            finally:
                context.close()
    except BrowserAuthCaptureError:
        raise
    except Exception as exc:
        raise BrowserAuthCaptureError(_browser_error_message(exc)) from exc
