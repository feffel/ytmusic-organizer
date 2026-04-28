from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable
from urllib.parse import urlparse


class BrowserAuthCaptureError(RuntimeError):
    """Raised when browser-assisted auth capture cannot produce usable headers."""


class PlaywrightChromiumMissingError(BrowserAuthCaptureError):
    """Raised when Playwright is present but its Chromium browser is missing."""


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


def is_missing_chromium_error(exc: BaseException) -> bool:
    message = str(exc)
    return (
        isinstance(exc, PlaywrightChromiumMissingError)
        or "Executable doesn't exist" in message
        or "playwright install" in message
        or "Automated browser support needs Chromium" in message
    )


def install_playwright_chromium(
    run_command: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> None:
    runner = run_command or subprocess.run
    command = [sys.executable, "-m", "playwright", "install", "chromium"]
    result = runner(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = redact_auth_secrets((result.stderr or result.stdout or "").strip())
        message = "Unable to install Playwright Chromium automatically."
        if detail:
            message += f" {detail}"
        raise BrowserAuthCaptureError(message)


def _browser_error_message(exc: Exception) -> str:
    message = redact_auth_secrets(str(exc))
    if "Executable doesn't exist" in message or "playwright install" in message:
        return "Automated browser support needs Chromium before capture can continue."
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
        if is_missing_chromium_error(exc):
            raise PlaywrightChromiumMissingError(_browser_error_message(exc)) from exc
        raise BrowserAuthCaptureError(_browser_error_message(exc)) from exc
