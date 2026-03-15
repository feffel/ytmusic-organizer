from __future__ import annotations

import importlib.resources
import json
from pathlib import Path
from typing import Any

from ytmusicapi import setup as ytmusic_setup

from .config import Config, load_or_create_config, save_config
from .paths import WorkspacePaths, ensure_workspace_dirs
from .planning import classify_with_openai, render_prompt, wait_for_json_file
from .setup_state import SetupState
from .ui import WizardUI
from .validation import validate_full_plan, validate_new_plan
from .ytmusic_ops import (
    apply_new_likes,
    apply_plan,
    delete_managed_playlists,
    export_liked,
    export_new_likes,
    initialize_state,
    make_ytmusic,
    preview_plan,
    update_managed_playlists,
)


def ensure_bootstrap_completed(marker_path: Path) -> None:
    if not marker_path.exists():
        raise RuntimeError("Setup has not been completed. Run `ytmo setup --workspace .ytmo`.")

    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Setup marker is invalid. Run `ytmo setup --workspace .ytmo` again.") from exc

    if not marker.get("completed"):
        raise RuntimeError("Setup has not been completed. Run `ytmo setup --workspace .ytmo`.")


def _set_bootstrap_completed(marker_path: Path, completed: bool = True) -> None:
    marker_path.write_text(json.dumps({"completed": completed}, indent=2), encoding="utf-8")


def cleanup_local_artifacts(workspace: Path) -> int:
    paths = WorkspacePaths(workspace)
    to_remove = [
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
    removed = 0
    for path in to_remove:
        if path.exists():
            path.unlink()
            removed += 1
    return removed


def _load_prompt_file(name: str) -> str:
    return importlib.resources.files("ytmusic_organizer.prompts").joinpath(name).read_text(encoding="utf-8")


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


def _load_managed_playlists(paths: WorkspacePaths) -> list[str]:
    if not paths.managed.exists():
        return []
    data = json.loads(paths.managed.read_text(encoding="utf-8"))
    playlists = data.get("playlists", [])
    return [str(name) for name in playlists if str(name).strip()]


def run_setup(
    workspace: Path,
    cwd: Path,
    auth_file: str | None,
    mode: str | None,
    interactive: bool,
    restart: bool = False,
) -> dict[str, Any]:
    ui = WizardUI()
    ui.title("ytmusic-organizer setup")

    paths = WorkspacePaths(workspace)
    ensure_workspace_dirs(paths)
    state = SetupState(paths.setup_state)
    if restart:
        state.reset()
        ui.warning("Setup state was reset. Starting from scratch.")

    config = load_or_create_config(paths.config)
    if auth_file:
        config.auth_file = auth_file
    if mode:
        config.classification_mode = mode

    if interactive and not mode:
        choice = input("Default classification mode [manual/api] (manual): ").strip().lower()
        if choice in {"manual", "api"}:
            config.classification_mode = choice

    save_config(paths.config, config)
    ui.success(f"Workspace ready at {paths.root}")

    try:
        auth_path = _resolve_auth_path(config.auth_file, paths.root)
        if not state.is_step_done("auth_ready"):
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
                ui.note("Starting interactive auth setup (ytmusicapi).")
                ui.note("Guide: https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html")
                ytmusic_setup(filepath=str(auth_path))

                if not auth_path.exists():
                    raise FileNotFoundError(f"Auth setup did not create file: {auth_path}")
            state.mark_step("auth_ready")
            ui.success("Auth ready")
        else:
            ui.note("Resuming: auth step already completed")

        yt = make_ytmusic(auth_path)
        mode = _effective_mode(mode, config)

        if not state.is_step_done("liked_exported") or not paths.liked_songs.exists():
            ui.step("Export full liked songs")
            liked = export_liked(yt, paths.liked_songs)
            state.mark_step("liked_exported")
            ui.success(f"Exported {len(liked)} liked songs")
        else:
            liked = json.loads(paths.liked_songs.read_text(encoding="utf-8"))
            ui.note("Resuming: liked songs export already completed")

        if not state.is_step_done("plan_ready") or not paths.playlist_plan.exists():
            ui.step("Generate or wait for playlist plan")
            _obtain_full_plan(mode, config, paths)
            state.mark_step("plan_ready")
            ui.success("Plan ready")
        else:
            ui.note("Resuming: plan step already completed")

        if not state.is_step_done("managed_updated") or not paths.managed.exists():
            ui.step("Update managed playlist index")
            update_managed_playlists(paths.playlist_plan, paths.managed)
            state.mark_step("managed_updated")
            ui.success("Managed playlist index updated")
        else:
            ui.note("Resuming: managed index already completed")

        if not state.is_step_done("playlists_applied"):
            ui.step("Create and fill playlists")
            apply_plan(
                yt=yt,
                liked_path=paths.liked_songs,
                plan_path=paths.playlist_plan,
                missing_path=paths.missing_matches,
                create_playlists=True,
            )
            state.mark_step("playlists_applied")
            ui.success("Playlists created/updated")
        else:
            ui.note("Resuming: apply step already completed")

        if not state.is_step_done("state_initialized") or not paths.state.exists():
            ui.step("Initialize incremental state")
            initialize_state(paths.liked_songs, paths.state)
            state.mark_step("state_initialized")
            ui.success("State initialized")
        else:
            ui.note("Resuming: state already initialized")

        _set_bootstrap_completed(paths.bootstrap, completed=True)
        state.complete()
        ui.success("Setup completed")
        return {"liked_count": len(liked), "workspace": str(paths.root)}
    except KeyboardInterrupt as exc:
        state.mark_error("setup interrupted by user")
        raise RuntimeError("Setup was interrupted. Re-run `ytmo setup --workspace .ytmo` to resume.") from exc
    except Exception as exc:
        state.mark_error(str(exc))
        raise


def _obtain_full_plan(mode: str, config: Config, paths: WorkspacePaths) -> dict[str, Any]:
    template = _load_prompt_file("gpt_prompt_full_reset.txt")
    songs = json.loads(paths.liked_songs.read_text(encoding="utf-8"))
    prompt_text = render_prompt(
        template,
        {"[PASTE CONTENTS OF liked_songs.json HERE]": json.dumps(songs, ensure_ascii=False, indent=2)},
    )
    prompt_path = paths.data_dir / "full_reset_prompt_filled.txt"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    if mode == "manual":
        print("Open prompt file:", prompt_path)
        print("Save model JSON response to:", paths.playlist_plan)
        plan = wait_for_json_file(paths.playlist_plan)
    else:
        plan = classify_with_openai(prompt_text, model=config.openai_model)
        paths.playlist_plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    return validate_full_plan(plan)


def _obtain_new_plan(mode: str, config: Config, paths: WorkspacePaths) -> dict[str, Any]:
    template = _load_prompt_file("gpt_prompt_new_songs.txt")
    songs = json.loads(paths.new_likes.read_text(encoding="utf-8"))
    managed = _load_managed_playlists(paths)
    playlist_lines = "\n".join(f"- {name}" for name in managed) if managed else "- (none)"
    prompt_text = render_prompt(
        template,
        {
            "[EXISTING_PLAYLISTS]": playlist_lines,
            "[PASTE CONTENTS OF new_likes.json HERE]": json.dumps(songs, ensure_ascii=False, indent=2),
        },
    )
    prompt_path = paths.data_dir / "new_songs_prompt_filled.txt"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    if mode == "manual":
        print("Open prompt file:", prompt_path)
        print("Save model JSON response to:", paths.new_plan)
        plan = wait_for_json_file(paths.new_plan)
    else:
        plan = classify_with_openai(prompt_text, model=config.openai_model)
        paths.new_plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    return validate_new_plan(plan)


def run_bootstrap(workspace: Path, cwd: Path, mode: str | None = None) -> dict[str, Any]:
    paths = WorkspacePaths(workspace)
    ensure_workspace_dirs(paths)
    config = load_or_create_config(paths.config)
    mode = _effective_mode(mode, config)

    auth_path = _resolve_auth_path(config.auth_file, paths.root)
    if not auth_path.exists():
        raise FileNotFoundError(f"Auth file not found: {auth_path}")

    yt = make_ytmusic(auth_path)

    liked = export_liked(yt, paths.liked_songs)
    _obtain_full_plan(mode, config, paths)

    update_managed_playlists(paths.playlist_plan, paths.managed)
    apply_plan(
        yt=yt,
        liked_path=paths.liked_songs,
        plan_path=paths.playlist_plan,
        missing_path=paths.missing_matches,
        create_playlists=True,
    )
    initialize_state(paths.liked_songs, paths.state)
    _set_bootstrap_completed(paths.bootstrap, completed=True)

    return {"liked_count": len(liked), "workspace": str(paths.root)}


def run_weekly_sync(workspace: Path, cwd: Path, mode: str | None = None) -> dict[str, Any]:
    paths = WorkspacePaths(workspace)
    ensure_workspace_dirs(paths)
    ensure_bootstrap_completed(paths.bootstrap)

    config = load_or_create_config(paths.config)
    mode = _effective_mode(mode, config)
    auth_path = _resolve_auth_path(config.auth_file, paths.root)
    yt = make_ytmusic(auth_path)

    new_likes = export_new_likes(yt, paths.state, paths.new_likes)
    if not new_likes:
        return {"new_likes": 0}

    _obtain_new_plan(mode, config, paths)
    result = apply_new_likes(yt, paths.new_likes, paths.new_plan, paths.state, paths.missing_matches)
    result["new_likes"] = len(new_likes)
    return result


def run_full_reset(workspace: Path, cwd: Path, mode: str | None = None) -> dict[str, Any]:
    paths = WorkspacePaths(workspace)
    ensure_workspace_dirs(paths)

    config = load_or_create_config(paths.config)
    mode = _effective_mode(mode, config)
    auth_path = _resolve_auth_path(config.auth_file, paths.root)
    yt = make_ytmusic(auth_path)

    liked = export_liked(yt, paths.liked_songs)
    _obtain_full_plan(mode, config, paths)

    update_managed_playlists(paths.playlist_plan, paths.managed)
    deleted = delete_managed_playlists(yt, paths.managed)
    apply_plan(
        yt=yt,
        liked_path=paths.liked_songs,
        plan_path=paths.playlist_plan,
        missing_path=paths.missing_matches,
        create_playlists=True,
    )
    initialize_state(paths.liked_songs, paths.state)
    _set_bootstrap_completed(paths.bootstrap, completed=True)

    return {"liked_count": len(liked), "deleted_playlists": deleted}


def run_preview(workspace: Path, plan_path: Path | None = None) -> dict[str, Any]:
    paths = WorkspacePaths(workspace)
    ensure_workspace_dirs(paths)
    selected_plan = plan_path or paths.playlist_plan
    plan_data = json.loads(selected_plan.read_text(encoding="utf-8"))
    validate_full_plan(plan_data)
    return preview_plan(paths.liked_songs, selected_plan, paths.missing_matches)


def run_cleanup(workspace: Path, cwd: Path, local_only: bool = False) -> dict[str, Any]:
    paths = WorkspacePaths(workspace)
    ensure_workspace_dirs(paths)

    deleted = 0
    if not local_only:
        config = load_or_create_config(paths.config)
        auth_path = _resolve_auth_path(config.auth_file, paths.root)
        if not auth_path.exists():
            raise FileNotFoundError(f"Auth file not found: {auth_path}")
        yt = make_ytmusic(auth_path)
        deleted = delete_managed_playlists(yt, paths.managed)

    removed_local = cleanup_local_artifacts(paths.root)
    return {"deleted_playlists": deleted, "removed_local_files": removed_local}
