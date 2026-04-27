from __future__ import annotations

import importlib.resources
import json
import os
from collections import Counter
from pathlib import Path
import sys
import tempfile
import termios
import time
from typing import Any, Callable

from ytmusicapi import setup as ytmusic_setup

from .auth_capture import capture_browser_auth_headers, redact_auth_secrets
from .config import Config, load_or_create_config, save_config
from .io_utils import atomic_write_text
from .paths import WorkspacePaths, ensure_workspace_dirs
from .planning import classify_with_openai, read_json_from_stdin, render_prompt
from .setup_state import SetupState
from .ui import WizardUI
from .validation import validate_full_plan, validate_new_plan
from .ytmusic_ops import (
    apply_new_likes,
    apply_plan,
    delete_managed_playlists,
    diagnose_plan_matches,
    export_liked,
    export_liked_data,
    export_new_likes,
    export_new_likes_data,
    initialize_state,
    make_ytmusic,
    simulate_apply_new_likes,
    simulate_apply_plan,
    simulate_delete_managed_playlists,
    update_managed_playlists,
)


def ensure_bootstrap_completed(marker_path: Path) -> None:
    if not marker_path.exists():
        raise RuntimeError("Setup has not been completed. Run `ytmo setup`.")

    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Setup marker is invalid. Run `ytmo setup` again.") from exc

    if not marker.get("completed"):
        raise RuntimeError("Setup has not been completed. Run `ytmo setup`.")


def _set_bootstrap_completed(marker_path: Path, completed: bool = True) -> None:
    atomic_write_text(marker_path, json.dumps({"completed": completed}, indent=2), encoding="utf-8")


def _cleanup_artifact_paths(paths: WorkspacePaths) -> list[Path]:
    return [
        paths.state,
        paths.managed,
        paths.bootstrap,
        paths.setup_state,
        paths.liked_songs,
        paths.new_likes,
        paths.playlist_plan,
        paths.new_plan,
        paths.missing_matches,
        paths.data_dir / "full_reset_prompt_filled.txt",
        paths.data_dir / "new_songs_prompt_filled.txt",
    ]


def count_cleanup_local_artifacts(workspace: Path) -> int:
    paths = WorkspacePaths(workspace)
    return sum(1 for path in _cleanup_artifact_paths(paths) if path.exists())


def cleanup_local_artifacts(workspace: Path) -> int:
    paths = WorkspacePaths(workspace)
    to_remove = _cleanup_artifact_paths(paths)
    removed = 0
    for path in to_remove:
        if path.exists():
            path.unlink()
            removed += 1
    return removed


def _load_prompt_file(name: str) -> str:
    return (
        importlib.resources.files("ytmusic_organizer.prompts")
        .joinpath(name)
        .read_text(encoding="utf-8")
    )


def _effective_mode(requested_mode: str | None, config: Config) -> str:
    mode = (requested_mode or config.classification_mode or "manual").strip().lower()
    if mode not in {"manual", "api"}:
        raise ValueError("mode must be one of: manual, api")
    return mode


def _resolve_auth_path(auth_file: str, workspace: Path) -> Path:
    path = Path(auth_file)
    if not path.is_absolute():
        path = (workspace / path).resolve()
    return path


def _load_config_readonly(path: Path) -> Config:
    if not path.exists():
        return Config()
    return load_or_create_config(path)


def _create_temp_prompt_path(prefix: str) -> Path:
    fd, raw_path = tempfile.mkstemp(prefix=prefix, suffix=".txt")
    os.close(fd)
    return Path(raw_path)


def _parse_auth_headers_text(raw_text: str) -> dict[str, str]:
    text = raw_text.strip()
    if not text:
        raise RuntimeError("AUTH_HEADERS_INVALID::No headers were provided.")

    headers: dict[str, str] = {}

    if text.lstrip().startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, dict):
            for key, value in parsed.items():
                normalized_key = str(key).strip().strip('"').strip("'").lower()
                normalized_value = str(value).strip()
                if normalized_key and normalized_value:
                    headers[normalized_key] = normalized_value
        elif parsed is not None:
            raise RuntimeError("AUTH_HEADERS_INVALID::Headers JSON must be an object.")

    if not headers:
        for line in text.splitlines():
            entry = line.strip()
            if not entry or entry in {"{", "}"}:
                continue
            if entry.endswith(","):
                entry = entry[:-1].rstrip()
            if ":" not in entry:
                continue

            key, value = entry.split(":", 1)
            normalized_key = key.strip().strip('"').strip("'").lower()
            normalized_value = value.strip().strip('"').strip("'")
            if normalized_key and normalized_value:
                headers[normalized_key] = normalized_value

    required = {"cookie", "x-goog-authuser"}
    missing = sorted(required - set(headers.keys()))
    if missing:
        raise RuntimeError(
            "AUTH_HEADERS_INVALID::Missing required header(s): " + ", ".join(missing)
        )

    return headers


def _normalize_auth_headers(raw_text: str) -> str:
    headers = _parse_auth_headers_text(raw_text)
    return "\n".join(f"{key}: {value}" for key, value in headers.items())


def _brace_delta(value: str) -> int:
    return value.count("{") - value.count("}")


def _normalize_completed_json_headers(raw_text: str) -> str:
    try:
        json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "AUTH_HEADERS_INVALID::Headers JSON is incomplete or malformed."
        ) from exc
    return _normalize_auth_headers(raw_text)


def _collect_auth_headers_from_line_reader(read_line: Callable[[], str]) -> str:
    raw_lines: list[str] = []
    json_lines: list[str] = []
    mode: str | None = None
    balance = 0

    while True:
        try:
            line = read_line()
        except EOFError:
            break

        stripped = line.strip()
        if mode is None:
            if not stripped:
                continue
            if stripped.startswith("{"):
                mode = "json"
                json_lines.append(line)
                balance += _brace_delta(line)
                if balance <= 0:
                    return _normalize_completed_json_headers("\n".join(json_lines))
            else:
                mode = "raw"
                raw_lines.append(line)
            continue

        if mode == "json":
            json_lines.append(line)
            balance += _brace_delta(line)
            if balance <= 0:
                return _normalize_completed_json_headers("\n".join(json_lines))
            continue

        if not stripped:
            return _normalize_auth_headers("\n".join(raw_lines))
        raw_lines.append(line)

    if mode == "json":
        return _normalize_completed_json_headers("\n".join(json_lines))
    return _normalize_auth_headers("\n".join(raw_lines))


def _iter_tty_lines(fd: int):
    current: list[str] = []
    while True:
        chunk = os.read(fd, 1)
        if not chunk:
            break

        char = chunk.decode("utf-8", errors="ignore")
        if char == "\x04":  # EOT fallback
            break

        if char in {"\r", "\n"}:
            yield "".join(current)
            current = []
            continue

        current.append(char)

    if current:
        yield "".join(current)


def _collect_auth_headers_from_tty() -> str:
    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)
    new_mode = termios.tcgetattr(fd)
    new_mode[3] &= ~termios.ICANON  # lflag
    new_mode[6][termios.VMIN] = 1
    new_mode[6][termios.VTIME] = 0

    try:
        termios.tcsetattr(fd, termios.TCSANOW, new_mode)
        tty_lines = iter(_iter_tty_lines(fd))

        def read_line() -> str:
            try:
                return next(tty_lines)
            except StopIteration as exc:
                raise EOFError from exc

        return _collect_auth_headers_from_line_reader(read_line)
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, original)


def _collect_auth_headers_from_stdin(ui: WizardUI | None = None) -> str:
    if ui:
        ui.note("Paste browser headers and press Enter.")
        ui.note("If you paste JSON, it auto-submits when the closing '}' appears.")
        ui.note("If you paste line-by-line headers, submit with one blank line.")
        ui.note("Format 1: cookie: <value>  |  x-goog-authuser: 1")
        ui.note('Format 2: {"cookie":"<value>","x-goog-authuser":"1",...}')
    else:
        print("Paste browser headers and press Enter.")
        print("If you paste JSON, it auto-submits when the closing '}' appears.")
        print("If you paste line-by-line headers, submit with one blank line.")
        print("Format 1: cookie: <value>  |  x-goog-authuser: 1")
        print('Format 2: {"cookie":"<value>","x-goog-authuser":"1",...}')

    if sys.stdin.isatty():
        return _collect_auth_headers_from_tty()

    return _collect_auth_headers_from_line_reader(input)


def _load_managed_playlists(paths: WorkspacePaths) -> list[str]:
    if not paths.managed.exists():
        return []
    data = json.loads(paths.managed.read_text(encoding="utf-8"))
    playlists = data.get("playlists", [])
    if data.get("schema_version") == 2:
        names = []
        for item in playlists:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if name:
                    names.append(name)
        return names
    return [str(name) for name in playlists if isinstance(name, str) and str(name).strip()]


def run_demo(
    workspace: Path,
    mode: str = "manual",
    emit_ui: bool = True,
) -> dict[str, Any]:
    selected_mode = (mode or "manual").strip().lower()
    if selected_mode not in {"manual", "api"}:
        raise ValueError("mode must be one of: manual, api")

    pace = emit_ui and sys.stdout.isatty()

    def pause(seconds: float) -> None:
        if pace:
            time.sleep(seconds)

    ui = WizardUI(enabled=emit_ui)
    ui.start_flow(
        title="ytmusic-organizer demo",
        steps=[
            "Auth check",
            "Export full liked songs",
            "Generate playlist plan",
            "Create and fill playlists",
            "Update managed playlist index",
            "Initialize incremental state",
        ],
    )
    ui.render_callout(
        "warning",
        "Demo mode only",
        ["No auth setup, no network calls, and no file changes."],
    )
    pause(0.6)

    ui.start_step("Auth check")
    ui.step_detail(f"Mode: {selected_mode}")
    ui.step_detail("Checking browser auth file (simulated)...")
    pause(0.8)
    ui.step_detail("Using sample browser headers: cookie and x-goog-authuser.")
    pause(0.8)
    ui.finish_step("Auth ready (simulated)")
    pause(0.5)

    fake_liked_count = 48
    ui.start_step("Export full liked songs")
    ui.step_detail("Fetching liked songs from YouTube Music (simulated)...")
    pause(1.0)
    ui.finish_step(f"Exported {fake_liked_count} liked songs (simulated)")
    pause(0.5)

    ui.start_step("Generate playlist plan")
    if selected_mode == "manual":
        ui.step_detail("Manual mode simulation: prompt opened and JSON pasted.")
        pause(0.9)
    else:
        ui.step_detail("API mode simulation: model returned validated plan JSON.")
        pause(0.9)
    fake_playlists = 7
    ui.finish_step(f"Plan ready with {fake_playlists} playlists (simulated)")
    pause(0.5)

    ui.start_step("Create and fill playlists")
    fake_added = 42
    fake_missing = 3
    ui.step_detail("Resolving matches and playlist diffs (simulated)...")
    pause(1.1)
    ui.finish_step(
        f"Playlists created/updated (simulated): added={fake_added}, missing={fake_missing}"
    )
    pause(0.5)

    ui.start_step("Update managed playlist index")
    ui.step_detail("Refreshing managed playlist IDs (simulated)...")
    pause(0.8)
    ui.finish_step("Managed playlist index updated (simulated)")
    pause(0.5)

    ui.start_step("Initialize incremental state")
    ui.step_detail("Saving processed IDs (simulated)...")
    pause(0.8)
    ui.finish_step("State initialized (simulated)")
    pause(0.6)
    ui.finish_flow("Demo completed (simulated)")

    return {
        "simulated": True,
        "workspace": str(workspace),
        "mode": selected_mode,
        "liked_count": fake_liked_count,
        "playlists_in_plan": fake_playlists,
        "would_add_items": fake_added,
        "missing": fake_missing,
    }


def run_setup(
    workspace: Path,
    auth_file: str | None,
    mode: str | None,
    interactive: bool,
    emit_ui: bool = True,
    restart: bool = False,
    dry_run: bool = False,
    auth_method: str = "auto",
) -> dict[str, Any]:
    selected_auth_method = (auth_method or "auto").strip().lower()
    if selected_auth_method not in {"auto", "browser", "manual"}:
        raise ValueError("auth_method must be one of: auto, browser, manual")

    ui = WizardUI(enabled=emit_ui)
    ui.start_flow(
        steps=[
            "Auth check",
            "Export full liked songs",
            "Generate playlist plan",
            "Create and fill playlists",
            "Update managed playlist index",
            "Initialize incremental state",
        ]
    )
    paths = WorkspacePaths(workspace)

    if dry_run:
        if restart:
            ui.warning("Ignoring --restart in dry-run mode.")
        config = _load_config_readonly(paths.config)
        if auth_file:
            config.auth_file = auth_file
        if mode:
            config.classification_mode = mode
        if interactive and not mode:
            choice = input("Default mode [manual/api] (manual): ").strip().lower()
            if choice in {"manual", "api"}:
                config.classification_mode = choice

        auth_path = _resolve_auth_path(config.auth_file, paths.root)
        if not auth_path.exists():
            explicit_auth_path = auth_file is not None
            if explicit_auth_path:
                raise FileNotFoundError(f"Auth file not found: {auth_path}")
            raise FileNotFoundError(
                f"Auth file not found: {auth_path}. Dry-run setup needs an existing auth file."
            )

        yt = make_ytmusic(auth_path)
        selected_mode = _effective_mode(mode, config)
        liked = export_liked_data(yt)
        temp_prompt = _create_temp_prompt_path("ytmo-full-plan-")
        try:
            plan = _obtain_full_plan(
                selected_mode,
                config,
                paths,
                ui=ui,
                interactive=interactive,
                songs_override=liked,
                prompt_path=temp_prompt,
                persist_plan=False,
            )
        finally:
            if temp_prompt.exists():
                temp_prompt.unlink()
        apply_result = simulate_apply_plan(yt, liked, plan, create_playlists=True)
        results = apply_result.get("results", [])
        return {
            "dry_run": True,
            "workspace": str(paths.root),
            "liked_count": len(liked),
            "playlists_in_plan": len(plan.get("playlists", [])),
            "would_create_playlists": sum(1 for item in results if item.get("status") == "created"),
            "would_reuse_playlists": sum(1 for item in results if item.get("status") == "reused"),
            "would_add_items": sum(int(item.get("added", 0)) for item in results),
            "missing": int(apply_result.get("missing", 0)),
        }

    ensure_workspace_dirs(paths)
    state = SetupState(paths.setup_state)
    if restart:
        state.reset()
        ui.warning("Setup state was reset. Starting from scratch.")
    tracked_setup_steps = (
        "auth_ready",
        "liked_exported",
        "plan_ready",
        "playlists_applied",
        "managed_updated",
        "state_initialized",
    )
    has_resume_progress = any(state.is_step_done(step) for step in tracked_setup_steps)

    config = _load_config_readonly(paths.config)
    if auth_file:
        config.auth_file = auth_file
    if mode:
        config.classification_mode = mode

    if interactive and not mode and not has_resume_progress:
        if emit_ui:
            ui.render_callout(
                "info",
                "Choose classification mode",
                [
                    "manual: free and fully controllable, but you must paste JSON output each run.",
                    "api: fastest flow with automatic plan generation, but requires OPENAI_API_KEY and API cost.",
                ],
            )
        try:
            choice = input("Default mode [manual/api] (manual): ").strip().lower()
        except (KeyboardInterrupt, EOFError) as exc:
            state.mark_error("setup interrupted by user")
            raise RuntimeError("Setup was interrupted. Re-run `ytmo setup` to resume.") from exc
        if choice in {"manual", "api"}:
            config.classification_mode = choice

    try:
        auth_path = _resolve_auth_path(config.auth_file, paths.root)
        if not state.is_step_done("auth_ready") or not auth_path.exists():
            ui.step("Auth check")
            if not auth_path.exists():
                explicit_auth_path = auth_file is not None
                if explicit_auth_path:
                    raise FileNotFoundError(f"Auth file not found: {auth_path}")

                if not interactive:
                    raise FileNotFoundError(
                        f"Auth file not found: {auth_path}. Run interactive setup or pass --auth-file."
                    )

                ui.warning("No auth file found in workspace.")
                if selected_auth_method in {"auto", "browser"}:
                    ui.note("Opening YouTube Music to capture browser auth automatically.")
                    ui.note("If prompted, log in and let the page finish loading.")
                    try:
                        headers_raw = capture_browser_auth_headers(workspace)
                    except Exception as exc:
                        if selected_auth_method == "browser":
                            raise
                        ui.warning("Browser auth capture failed: " + redact_auth_secrets(str(exc)))
                        ui.note("Falling back to manual browser header paste.")
                        ui.note(
                            "Guide: https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html"
                        )
                        headers_raw = _collect_auth_headers_from_stdin(ui=ui)
                    else:
                        ui.success("Captured browser auth headers")
                else:
                    ui.note("Starting browser auth setup (from browser network request headers).")
                    ui.note("Guide: https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html")
                    headers_raw = _collect_auth_headers_from_stdin(ui=ui)
                ytmusic_setup(filepath=str(auth_path), headers_raw=headers_raw)

                if not auth_path.exists():
                    raise FileNotFoundError(f"Auth setup did not create file: {auth_path}")
            state.mark_step("auth_ready")
            ui.success("Auth ready")
        else:
            ui.replay_completed_step("Auth check already completed")

        save_config(paths.config, config)
        ui.success(f"Workspace ready at {paths.root}")

        yt = make_ytmusic(auth_path)
        selected_mode = _effective_mode(mode, config)

        if not state.is_step_done("liked_exported") or not paths.liked_songs.exists():
            ui.step("Export full liked songs")
            liked = export_liked(yt, paths.liked_songs)
            state.mark_step("liked_exported")
            ui.success(f"Exported {len(liked)} liked songs")
        else:
            liked = json.loads(paths.liked_songs.read_text(encoding="utf-8"))
            ui.replay_completed_step("Export full liked songs already completed")

        if not state.is_step_done("plan_ready") or not paths.playlist_plan.exists():
            ui.step("Generate or wait for playlist plan")
            _obtain_full_plan(selected_mode, config, paths, ui=ui, interactive=interactive)
            state.mark_step("plan_ready")
            ui.success("Plan ready")
        else:
            ui.replay_completed_step("Generate or wait for playlist plan already completed")

        if not state.is_step_done("playlists_applied"):
            ui.step("Create and fill playlists")
            apply_result = apply_plan(
                yt=yt,
                liked_path=paths.liked_songs,
                plan_path=paths.playlist_plan,
                missing_path=paths.missing_matches,
                create_playlists=True,
            )
            state.mark_step("playlists_applied")
            ui.success("Playlists created/updated")
        else:
            apply_result = {"results": []}
            ui.replay_completed_step("Create and fill playlists already completed")

        if not state.is_step_done("managed_updated") or not paths.managed.exists():
            ui.step("Update managed playlist index")
            update_managed_playlists(apply_result.get("results", []), paths.managed)
            state.mark_step("managed_updated")
            ui.success("Managed playlist index updated")
        else:
            ui.replay_completed_step("Update managed playlist index already completed")

        if not state.is_step_done("state_initialized") or not paths.state.exists():
            ui.step("Initialize incremental state")
            initialize_state(paths.liked_songs, paths.state)
            state.mark_step("state_initialized")
            ui.success("State initialized")
        else:
            ui.replay_completed_step("Initialize incremental state already completed")

        _set_bootstrap_completed(paths.bootstrap, completed=True)
        state.complete()
        ui.success("Setup completed")
        return {"liked_count": len(liked), "workspace": str(paths.root)}
    except KeyboardInterrupt as exc:
        state.mark_error("setup interrupted by user")
        raise RuntimeError("Setup was interrupted. Re-run `ytmo setup` to resume.") from exc
    except Exception as exc:
        state.mark_error(str(exc))
        raise


def _obtain_full_plan(
    mode: str,
    config: Config,
    paths: WorkspacePaths,
    ui: WizardUI | None = None,
    interactive: bool = True,
    songs_override: list[dict[str, Any]] | None = None,
    prompt_path: Path | None = None,
    plan_output_path: Path | None = None,
    persist_plan: bool = True,
) -> dict[str, Any]:
    template = _load_prompt_file("gpt_prompt_full_reset.txt")
    songs = (
        songs_override
        if songs_override is not None
        else json.loads(paths.liked_songs.read_text(encoding="utf-8"))
    )
    prompt_text = render_prompt(
        template,
        {
            "[PASTE CONTENTS OF liked_songs.json HERE]": json.dumps(
                songs, ensure_ascii=False, indent=2
            )
        },
    )
    selected_prompt_path = prompt_path or (paths.data_dir / "full_reset_prompt_filled.txt")
    atomic_write_text(selected_prompt_path, prompt_text, encoding="utf-8")
    selected_plan_output = (
        plan_output_path
        if plan_output_path is not None
        else (paths.playlist_plan if persist_plan else None)
    )

    if mode == "manual":
        if ui:
            ui.render_callout(
                "info",
                "Manual classification required",
                [
                    f"Open prompt file: {selected_prompt_path}",
                    "Use this prompt with your AI tool.",
                    "Paste back the full output JSON and press Enter.",
                    "JSON auto-submits when closing braces are complete; otherwise submit with one blank line.",
                ],
            )
        else:
            print("Open prompt file:", selected_prompt_path)
            print("Use this prompt with your AI tool.")
            print("Paste back the full output JSON and press Enter.")
            print(
                "JSON auto-submits when closing braces are complete; otherwise submit with one blank line."
            )
        plan = read_json_from_stdin()
        if selected_plan_output:
            atomic_write_text(
                selected_plan_output,
                json.dumps(plan, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    else:
        plan = classify_with_openai(prompt_text, model=config.openai_model)
        if selected_plan_output:
            atomic_write_text(
                selected_plan_output,
                json.dumps(plan, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    return validate_full_plan(plan)


def _obtain_new_plan(
    mode: str,
    config: Config,
    paths: WorkspacePaths,
    ui: WizardUI | None = None,
    interactive: bool = True,
    songs_override: list[dict[str, Any]] | None = None,
    managed_override: list[str] | None = None,
    prompt_path: Path | None = None,
    plan_output_path: Path | None = None,
    persist_plan: bool = True,
) -> dict[str, Any]:
    template = _load_prompt_file("gpt_prompt_new_songs.txt")
    songs = (
        songs_override
        if songs_override is not None
        else json.loads(paths.new_likes.read_text(encoding="utf-8"))
    )
    managed = managed_override if managed_override is not None else _load_managed_playlists(paths)
    playlist_lines = "\n".join(f"- {name}" for name in managed) if managed else "- (none)"
    prompt_text = render_prompt(
        template,
        {
            "[EXISTING_PLAYLISTS]": playlist_lines,
            "[PASTE CONTENTS OF new_likes.json HERE]": json.dumps(
                songs, ensure_ascii=False, indent=2
            ),
        },
    )
    selected_prompt_path = prompt_path or (paths.data_dir / "new_songs_prompt_filled.txt")
    atomic_write_text(selected_prompt_path, prompt_text, encoding="utf-8")
    selected_plan_output = (
        plan_output_path
        if plan_output_path is not None
        else (paths.new_plan if persist_plan else None)
    )

    if mode == "manual":
        if ui:
            ui.render_callout(
                "info",
                "Manual classification required",
                [
                    f"Open prompt file: {selected_prompt_path}",
                    "Use this prompt with your AI tool.",
                    "Paste back the full output JSON and press Enter.",
                    "JSON auto-submits when closing braces are complete; otherwise submit with one blank line.",
                ],
            )
        else:
            print("Open prompt file:", selected_prompt_path)
            print("Use this prompt with your AI tool.")
            print("Paste back the full output JSON and press Enter.")
            print(
                "JSON auto-submits when closing braces are complete; otherwise submit with one blank line."
            )
        plan = read_json_from_stdin()
        if selected_plan_output:
            atomic_write_text(
                selected_plan_output,
                json.dumps(plan, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    else:
        plan = classify_with_openai(prompt_text, model=config.openai_model)
        if selected_plan_output:
            atomic_write_text(
                selected_plan_output,
                json.dumps(plan, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    return validate_new_plan(plan)


def run_weekly_sync(
    workspace: Path,
    mode: str | None = None,
    interactive: bool = True,
    emit_ui: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    paths = WorkspacePaths(workspace)
    ui = WizardUI(enabled=emit_ui)
    ui.start_flow(
        steps=[
            "Export new likes",
            "Generate or wait for new-likes plan",
            "Apply playlist updates",
        ]
    )
    if not dry_run:
        ensure_workspace_dirs(paths)
    ensure_bootstrap_completed(paths.bootstrap)

    config = _load_config_readonly(paths.config) if dry_run else load_or_create_config(paths.config)
    selected_mode = _effective_mode(mode, config)
    auth_path = _resolve_auth_path(config.auth_file, paths.root)
    if not auth_path.exists():
        raise FileNotFoundError(f"Auth file not found: {auth_path}")
    yt = make_ytmusic(auth_path)

    ui.start_step("Export new likes")
    if dry_run:
        state_data = (
            json.loads(paths.state.read_text(encoding="utf-8"))
            if paths.state.exists()
            else {"processed_video_ids": []}
        )
        processed_ids = set(state_data.get("processed_video_ids", []))
        new_likes = export_new_likes_data(yt, processed_ids)
    else:
        new_likes = export_new_likes(yt, paths.state, paths.new_likes)
    ui.finish_step(f"Detected {len(new_likes)} new likes")

    if not new_likes:
        ui.finish_flow("Sync completed: no new likes")
        if dry_run:
            return {"dry_run": True, "new_likes": 0}
        return {"new_likes": 0}

    ui.start_step("Generate or wait for new-likes plan")
    if dry_run:
        temp_prompt = _create_temp_prompt_path("ytmo-new-plan-")
        managed = _load_managed_playlists(paths)
        try:
            plan = _obtain_new_plan(
                selected_mode,
                config,
                paths,
                ui=ui,
                interactive=interactive,
                songs_override=new_likes,
                managed_override=managed,
                prompt_path=temp_prompt,
                persist_plan=False,
            )
        finally:
            if temp_prompt.exists():
                temp_prompt.unlink()
        ui.finish_step("Plan ready")
        ui.start_step("Apply playlist updates")
        preview = simulate_apply_new_likes(
            yt,
            new_likes,
            plan,
            current_state=state_data,
        )
        results = preview.get("results", [])
        ui.finish_step(
            "Previewed playlist updates: "
            f"would_add={sum(int(item.get('added', 0)) for item in results)}"
        )
        ui.finish_flow("Sync dry-run completed")
        return {
            "dry_run": True,
            "new_likes": len(new_likes),
            "playlists_in_plan": len(plan.get("playlists", [])),
            "would_add_items": sum(int(item.get("added", 0)) for item in results),
            "would_mark_processed": int(preview.get("processed", 0)),
            "missing": int(preview.get("missing", 0)),
        }

    _obtain_new_plan(selected_mode, config, paths, ui=ui, interactive=interactive)
    ui.finish_step("Plan ready")
    ui.start_step("Apply playlist updates")
    result = apply_new_likes(
        yt, paths.new_likes, paths.new_plan, paths.state, paths.missing_matches
    )
    result["new_likes"] = len(new_likes)
    ui.finish_step(
        f"Updated playlists with {result.get('new_likes', 0)} new likes; missing={result.get('missing', 0)}"
    )
    ui.finish_flow("Sync completed")
    return result


def run_full_reset(
    workspace: Path,
    mode: str | None = None,
    interactive: bool = True,
    emit_ui: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    paths = WorkspacePaths(workspace)
    ui = WizardUI(enabled=emit_ui)
    ui.start_flow(
        steps=[
            "Export full liked songs",
            "Generate or wait for playlist plan",
            "Delete managed playlists",
            "Create and fill playlists",
            "Finalize managed state",
        ]
    )
    if not dry_run:
        ensure_workspace_dirs(paths)

    config = _load_config_readonly(paths.config) if dry_run else load_or_create_config(paths.config)
    selected_mode = _effective_mode(mode, config)
    auth_path = _resolve_auth_path(config.auth_file, paths.root)
    if not auth_path.exists():
        raise FileNotFoundError(f"Auth file not found: {auth_path}")
    yt = make_ytmusic(auth_path)

    ui.start_step("Export full liked songs")
    liked = export_liked_data(yt) if dry_run else export_liked(yt, paths.liked_songs)
    ui.finish_step(f"Exported {len(liked)} liked songs")
    ui.start_step("Generate or wait for playlist plan")
    if dry_run:
        temp_prompt = _create_temp_prompt_path("ytmo-full-plan-")
        try:
            plan = _obtain_full_plan(
                selected_mode,
                config,
                paths,
                ui=ui,
                interactive=interactive,
                songs_override=liked,
                prompt_path=temp_prompt,
                persist_plan=False,
            )
        finally:
            if temp_prompt.exists():
                temp_prompt.unlink()
        ui.finish_step("Plan ready")

        ui.start_step("Delete managed playlists")
        delete_result = simulate_delete_managed_playlists(yt, paths.managed)
        ui.finish_step(
            f"Would delete {int(delete_result.get('would_delete', 0))} managed playlists"
        )
        ui.start_step("Create and fill playlists")
        apply_result = simulate_apply_plan(
            yt=yt,
            liked_tracks=liked,
            plan=plan,
            create_playlists=True,
        )
        results = apply_result.get("results", [])
        ui.finish_step(
            f"Would create {sum(1 for item in results if item.get('status') == 'created')} playlists"
        )
        ui.start_step("Finalize managed state")
        ui.finish_step("Dry-run does not mutate managed state")
        ui.finish_flow("Rebuild dry-run completed")
        return {
            "dry_run": True,
            "liked_count": len(liked),
            "playlists_in_plan": len(plan.get("playlists", [])),
            "would_delete_playlists": int(delete_result.get("would_delete", 0)),
            "skipped_legacy_count": len(delete_result.get("skipped_legacy", [])),
            "skipped_legacy": delete_result.get("skipped_legacy", []),
            "would_create_playlists": sum(1 for item in results if item.get("status") == "created"),
            "would_add_items": sum(int(item.get("added", 0)) for item in results),
            "missing": int(apply_result.get("missing", 0)),
        }

    _obtain_full_plan(selected_mode, config, paths, ui=ui, interactive=interactive)
    ui.finish_step("Plan ready")

    ui.start_step("Delete managed playlists")
    delete_result = delete_managed_playlists(yt, paths.managed)
    ui.finish_step(f"Deleted {delete_result.get('deleted', 0)} managed playlists")
    ui.start_step("Create and fill playlists")
    apply_result = apply_plan(
        yt=yt,
        liked_path=paths.liked_songs,
        plan_path=paths.playlist_plan,
        missing_path=paths.missing_matches,
        create_playlists=True,
    )
    ui.finish_step("Playlists created/updated")
    ui.start_step("Finalize managed state")
    update_managed_playlists(apply_result.get("results", []), paths.managed)
    initialize_state(paths.liked_songs, paths.state)
    _set_bootstrap_completed(paths.bootstrap, completed=True)
    ui.finish_step("Managed playlist index and state refreshed")
    ui.finish_flow("Rebuild completed")

    return {
        "liked_count": len(liked),
        "deleted_playlists": delete_result.get("deleted", 0),
        "skipped_legacy": delete_result.get("skipped_legacy", []),
    }


def run_cleanup(workspace: Path, local_only: bool = False, dry_run: bool = False) -> dict[str, Any]:
    paths = WorkspacePaths(workspace)
    if not dry_run:
        ensure_workspace_dirs(paths)
    return _run_cleanup(paths=paths, local_only=local_only, dry_run=dry_run)


def _run_cleanup(
    paths: WorkspacePaths, local_only: bool = False, dry_run: bool = False
) -> dict[str, Any]:
    if dry_run:
        would_remove = count_cleanup_local_artifacts(paths.root)
        preview = {"would_delete": 0, "skipped_legacy": []}
        if not local_only:
            preview = simulate_delete_managed_playlists(None, paths.managed)
            # Resolve against live library only when auth is available.
            if preview.get("would_delete", 0) > 0:
                config = _load_config_readonly(paths.config)
                auth_path = _resolve_auth_path(config.auth_file, paths.root)
                if auth_path.exists():
                    yt = make_ytmusic(auth_path)
                    preview = simulate_delete_managed_playlists(yt, paths.managed)
        return {
            "dry_run": True,
            "local_only": local_only,
            "would_delete_playlists": int(preview.get("would_delete", 0)),
            "would_remove_local_files": would_remove,
            "skipped_legacy_count": len(preview.get("skipped_legacy", [])),
            "skipped_legacy": preview.get("skipped_legacy", []),
        }

    deleted = 0
    skipped_legacy: list[str] = []
    remote_delete_error: str | None = None
    if not local_only:
        config = _load_config_readonly(paths.config)
        auth_path = _resolve_auth_path(config.auth_file, paths.root)
        if auth_path.exists():
            yt = make_ytmusic(auth_path)
            delete_result = delete_managed_playlists(yt, paths.managed)
            deleted = delete_result.get("deleted", 0)
            skipped_legacy = delete_result.get("skipped_legacy", [])
        else:
            remote_delete_error = f"Auth file not found: {auth_path}"

    removed_local = cleanup_local_artifacts(paths.root)
    result = {
        "deleted_playlists": deleted,
        "removed_local_files": removed_local,
        "skipped_legacy": skipped_legacy,
    }
    if remote_delete_error:
        result["remote_delete_error"] = remote_delete_error
    return result


def _read_json_file(
    path: Path, *, warnings: list[str] | None = None, label: str | None = None
) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        if warnings is not None:
            subject = label or str(path)
            warnings.append(f"{subject} could not be parsed: {exc}")
        return None


def _derive_stats_insights(
    *,
    liked_count: int,
    processed_count: int,
    managed_count: int,
    pending_count: int,
    validated_plan: dict[str, Any] | None,
    plan_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    plan_playlists = 0
    top_playlists: list[dict[str, Any]] = []
    if isinstance(validated_plan, dict):
        playlists = validated_plan.get("playlists", [])
        if isinstance(playlists, list):
            ranked: list[dict[str, Any]] = []
            for item in playlists:
                if not isinstance(item, dict):
                    continue
                songs = item.get("songs", [])
                songs_count = len(songs) if isinstance(songs, list) else 0
                sample_songs: list[str] = []
                artist_counts: Counter[str] = Counter()
                if isinstance(songs, list):
                    for song in songs:
                        if not isinstance(song, dict):
                            continue
                        title = str(song.get("title", "")).strip()
                        artist = str(song.get("artist", "")).strip()
                        if artist:
                            artist_counts[artist] += 1
                        if len(sample_songs) < 3:
                            if title and artist:
                                sample_songs.append(f"{title} - {artist}")
                            elif title:
                                sample_songs.append(title)
                row = {
                    "name": str(item.get("name", "Unnamed")),
                    "songs": songs_count,
                    "sample_songs": sample_songs,
                }
                description = item.get("description")
                if isinstance(description, str) and description.strip():
                    row["description"] = description.strip()
                artist_leaders = sorted(
                    artist_counts.items(),
                    key=lambda pair: (-pair[1], pair[0].casefold()),
                )
                if artist_leaders:
                    artist, count = artist_leaders[0]
                    suffix = "track" if count == 1 else "tracks"
                    row["top_artist"] = f"{artist} ({count} {suffix})"
                if len(artist_leaders) > 1:
                    artist, count = artist_leaders[1]
                    suffix = "track" if count == 1 else "tracks"
                    row["runner_up_artist"] = f"{artist} ({count} {suffix})"
                ranked.append(row)
            ranked.sort(key=lambda row: row["songs"], reverse=True)
            plan_playlists = len(ranked)
            top_playlists = ranked[:3]

    coverage_ratio = (processed_count / liked_count) if liked_count else 0.0

    if liked_count >= 1000:
        collection_shape = "Deep collection"
    elif liked_count >= 250:
        collection_shape = "Growing catalog"
    elif liked_count > 0:
        collection_shape = "Early collection"
    else:
        collection_shape = "Just getting started"

    if pending_count >= 25:
        pending_momentum = "High momentum"
    elif pending_count > 0:
        pending_momentum = "Steady momentum"
    else:
        pending_momentum = "No pending momentum"

    identity_score = 0
    if plan_diagnostics.get("status") == "ok":
        identity_score = min(
            100,
            int((coverage_ratio * 65.0) + min(plan_playlists, 15) * 2 + min(managed_count, 10) * 1),
        )

    return {
        "identity_score": identity_score,
        "plan_playlists": plan_playlists,
        "top_playlists": top_playlists,
        "coverage_ratio": round(coverage_ratio, 4),
        "collection_shape": collection_shape,
        "pending_momentum": pending_momentum,
    }


def run_stats(workspace: Path, plan_path: Path | None = None) -> dict[str, Any]:
    paths = WorkspacePaths(workspace)
    warnings: list[str] = []

    state = _read_json_file(paths.state, warnings=warnings, label="state.json")
    managed = _read_json_file(paths.managed, warnings=warnings, label="managed_playlists.json")
    missing = _read_json_file(
        paths.missing_matches, warnings=warnings, label="data/missing_matches.json"
    )
    new_likes = _read_json_file(paths.new_likes, warnings=warnings, label="data/new_likes.json")
    liked = _read_json_file(paths.liked_songs, warnings=warnings, label="data/liked_songs.json")

    processed_ids: list[str] = []
    if isinstance(state, dict):
        ids = state.get("processed_video_ids", [])
        if isinstance(ids, list):
            processed_ids = ids
        else:
            warnings.append(
                "state.json format is invalid. Recreate it with `ytmo setup` or `ytmo rebuild`."
            )
    elif state is not None:
        warnings.append(
            "state.json format is invalid. Recreate it with `ytmo setup` or `ytmo rebuild`."
        )

    playlist_items: list[Any] = []
    if isinstance(managed, dict):
        playlists = managed.get("playlists", [])
        if isinstance(playlists, list):
            playlist_items = playlists
        else:
            warnings.append(
                "managed_playlists.json format is invalid. Recreate it with `ytmo rebuild`."
            )
    elif managed is not None:
        warnings.append(
            "managed_playlists.json format is invalid. Recreate it with `ytmo rebuild`."
        )

    if isinstance(missing, list):
        missing_matches = len(missing)
    elif isinstance(missing, dict):
        missing_matches = len(missing.get("missing", []))
    else:
        if missing is not None:
            warnings.append("data/missing_matches.json format is invalid.")
        missing_matches = 0

    if new_likes is not None and not isinstance(new_likes, list):
        warnings.append("data/new_likes.json format is invalid.")
        new_likes = None

    if liked is not None and not isinstance(liked, list):
        warnings.append("data/liked_songs.json format is invalid.")
        liked = None

    selected_plan = plan_path.resolve() if plan_path else paths.playlist_plan
    validated_plan: dict[str, Any] | None = None
    plan_diagnostics: dict[str, Any] = {
        "status": "skipped_missing_plan",
        "plan_path": str(selected_plan),
        "liked_path": str(paths.liked_songs),
    }

    if selected_plan.exists():
        if not paths.liked_songs.exists():
            plan_diagnostics["status"] = "skipped_missing_liked"
        else:
            plan_data = _read_json_file(
                selected_plan,
                warnings=warnings,
                label=f"plan file ({selected_plan})",
            )
            if not isinstance(plan_data, dict):
                if plan_data is not None:
                    warnings.append(f"Plan file format is invalid: {selected_plan}.")
                plan_diagnostics["status"] = "invalid_plan"
            else:
                try:
                    validated_plan = validate_full_plan(plan_data)
                except Exception as exc:
                    warnings.append(f"Plan file failed validation: {selected_plan}: {exc}")
                    plan_diagnostics["status"] = "invalid_plan"
                else:
                    if not isinstance(liked, list):
                        plan_diagnostics["status"] = "invalid_liked"
                    else:
                        diagnostics = diagnose_plan_matches(liked, validated_plan)
                        plan_diagnostics["status"] = "ok"
                        plan_diagnostics.update(diagnostics)

    artifact_presence = {
        "config": paths.config.exists(),
        "state": paths.state.exists(),
        "managed_playlists": paths.managed.exists(),
        "liked_songs": paths.liked_songs.exists(),
        "new_likes": paths.new_likes.exists(),
        "playlist_plan": paths.playlist_plan.exists(),
        "new_plan": paths.new_plan.exists(),
        "missing_matches": paths.missing_matches.exists(),
    }
    required_artifact_keys = (
        "config",
        "state",
        "managed_playlists",
        "liked_songs",
        "playlist_plan",
    )
    missing_required_artifacts = [
        key for key in required_artifact_keys if not bool(artifact_presence.get(key))
    ]
    managed_playlist_names = [
        str(item.get("name")).strip()
        for item in playlist_items
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    ]
    artifact_paths = {
        "config": str(paths.config),
        "state": str(paths.state),
        "managed_playlists": str(paths.managed),
        "liked_songs": str(paths.liked_songs),
        "new_likes": str(paths.new_likes),
        "playlist_plan": str(paths.playlist_plan),
        "new_plan": str(paths.new_plan),
        "missing_matches": str(paths.missing_matches),
    }
    insights = _derive_stats_insights(
        liked_count=len(liked) if isinstance(liked, list) else 0,
        processed_count=len(processed_ids) if isinstance(processed_ids, list) else 0,
        managed_count=len(playlist_items) if isinstance(playlist_items, list) else 0,
        pending_count=len(new_likes) if isinstance(new_likes, list) else 0,
        validated_plan=validated_plan,
        plan_diagnostics=plan_diagnostics,
    )

    return {
        "workspace_exists": paths.root.exists(),
        "processed_likes": len(processed_ids) if isinstance(processed_ids, list) else 0,
        "managed_playlists": len(playlist_items) if isinstance(playlist_items, list) else 0,
        "missing_matches": missing_matches,
        "new_likes_pending": len(new_likes) if isinstance(new_likes, list) else 0,
        "liked_snapshot_count": len(liked) if isinstance(liked, list) else 0,
        "artifact_presence": artifact_presence,
        "artifact_paths": artifact_paths,
        "missing_required_artifacts": missing_required_artifacts,
        "managed_playlist_names": managed_playlist_names,
        "plan_diagnostics": plan_diagnostics,
        "insights": insights,
        "warnings": warnings,
    }
