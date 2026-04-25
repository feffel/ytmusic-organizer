from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .paths import default_workspace
from .ui import WizardUI
from .workflows import run_cleanup, run_demo, run_full_reset, run_setup, run_stats, run_weekly_sync


class _YtmoArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        setattr(self, "_ytmo_last_error", message)
        raise argparse.ArgumentError(None, message)


def _warn_legacy_root_artifacts(ui: WizardUI, workspace: Path, cwd: Path) -> None:
    if workspace == cwd:
        return
    legacy = [
        cwd / "browser.json",
        cwd / "state.json",
        cwd / "managed_playlists.json",
        cwd / "data",
    ]
    found = [path.name for path in legacy if path.exists()]
    if found:
        ui.warning(
            "Found older local files in this folder ("
            + ", ".join(found)
            + f"). Active workspace is {workspace}. "
            "Move or delete these old local files if they are stale, or pass "
            f"--workspace {cwd} if this folder is intentional."
        )


def build_helpful_error(exc: BaseException) -> str:
    if isinstance(exc, (KeyboardInterrupt, EOFError)):
        return (
            "Operation cancelled by user.\n"
            "How to continue:\n"
            "1. Re-run the same command when ready.\n"
            "2. Use --non-interactive for automation-safe runs where supported."
        )

    text = str(exc)

    if text.startswith("AUTH_HEADERS_INVALID::"):
        reason = text.replace("AUTH_HEADERS_INVALID::", "", 1)
        return (
            "Auth headers are incomplete or malformed.\n"
            f"{reason}\n\n"
            "How to fix:\n"
            "1. Re-run setup and paste full browser headers.\n"
            "2. For JSON headers, paste through the closing '}'.\n"
            "3. For raw header lines, finish with one blank line.\n"
            "4. Include at least these headers: cookie, x-goog-authuser.\n"
            "5. Use either raw header lines or JSON object format from browser network tools."
        )

    if "Auth file not found:" in text:
        return (
            f"Auth file is missing.\n"
            f"{text}\n\n"
            "How to fix:\n"
            "1. Run interactive setup (recommended):\n"
            "   ytmo setup\n"
            "   This creates <workspace>/browser.json for you.\n"
            "2. If you already have a file, pass it explicitly:\n"
            "   ytmo setup --auth-file /absolute/path/to/browser.json\n"
            "3. Dry-run still requires readable auth and may call network APIs.\n"
            "4. Auth guide reference:\n"
            "   https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html"
        )

    if "Setup has not been completed" in text:
        return (
            "Setup is incomplete.\n"
            f"{text}\n\n"
            "How to fix:\n"
            "1. Run guided setup:\n"
            "   ytmo setup\n"
            "2. Then retry your original command:\n"
            "   ytmo sync  (weekly updates)\n"
            "   ytmo rebuild --yes  (full rebuild)"
        )

    if "Setup was interrupted" in text:
        return (
            "Setup was interrupted.\n"
            "How to fix:\n"
            "1. Re-run setup to resume from the last completed step:\n"
            "   ytmo setup\n"
            "2. To restart from scratch:\n"
            "   ytmo setup --restart"
        )

    if "OPENAI_API_KEY is required for --mode api" in text:
        return (
            "API mode requires an OpenAI key.\n"
            "How to fix:\n"
            "1. Set OPENAI_API_KEY in your shell environment.\n"
            "2. Re-run the same command with --mode api.\n"
            "3. Or run in manual mode instead:\n"
            "   ytmo <command> --mode manual"
        )

    if "must be an array" in text or ".artist must be a non-empty string" in text:
        return (
            "Plan output is not valid JSON.\n"
            f"Validation error: {text}\n\n"
            "How to fix:\n"
            "1. Re-open the generated prompt file.\n"
            "2. Ask the model to return only valid JSON.\n"
            "3. Paste the corrected JSON and run again."
        )

    if "--yes is required when --non-interactive is set for rebuild" in text:
        return (
            "Non-interactive rebuild requires explicit destructive confirmation.\n"
            "How to fix:\n"
            "1. Re-run rebuild with --yes.\n"
            "2. Or remove --non-interactive to confirm interactively."
        )

    if "Invalid JSON input:" in text or text.startswith("Invalid JSON"):
        reason = text.split(":", 1)[1].strip() if ":" in text else text
        return (
            "Plan output is not valid JSON.\n"
            f"{reason}\n\n"
            "How to fix:\n"
            "1. Paste only JSON (no extra commentary).\n"
            "2. Make sure the top-level value is an object.\n"
            "3. Submit again."
        )

    if "No JSON received" in text:
        return (
            "No plan JSON was provided.\n"
            "How to fix:\n"
            "1. Paste your model JSON response.\n"
            "2. Press Enter to submit."
        )

    return f"Error: {text}"


def _find_subcommand(argv: list[str], subcommands: set[str]) -> str | None:
    for token in argv:
        if token == "--":
            break
        if token in subcommands:
            return token
        if token.startswith("-"):
            continue
        return None
    return None


def _emit_scoped_parse_help(parser: argparse.ArgumentParser, argv: list[str], message: str) -> None:
    print(f"{parser.prog}: error: {message}", file=sys.stderr)
    print(file=sys.stderr)
    subparsers_by_name = getattr(parser, "_ytmo_subparsers", {})
    subcommand = _find_subcommand(argv, set(subparsers_by_name))
    target = subparsers_by_name.get(subcommand, parser)
    target.print_help(sys.stderr)


def _base_parser(*, exit_on_error: bool = True) -> argparse.ArgumentParser:
    parser = _YtmoArgumentParser(
        prog="ytmo",
        description=f"YouTube Music Organizer CLI (v{__version__})",
        formatter_class=argparse.RawTextHelpFormatter,
        exit_on_error=exit_on_error,
        epilog=(
            "Most common commands:\n"
            "  ytmo setup\n"
            "  ytmo sync\n"
            "  ytmo rebuild --dry-run\n"
            "  ytmo stats"
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True, parser_class=_YtmoArgumentParser)
    subparsers_by_name: dict[str, argparse.ArgumentParser] = {}

    def add_workspace_argument(command_parser: argparse.ArgumentParser) -> None:
        default_path = str(default_workspace())
        command_parser.add_argument(
            "--workspace",
            default=default_path,
            help=f"Workspace directory (default: {default_path})",
        )

    def add_json_argument(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Print machine-readable JSON output",
        )

    def add_dry_run_argument(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate actions without mutating remote/workspace state; may still require auth/network reads",
        )

    p_setup = sub.add_parser("setup", help="Guided first-time setup and initial playlist build")
    add_workspace_argument(p_setup)
    add_json_argument(p_setup)
    add_dry_run_argument(p_setup)
    p_setup.add_argument("--mode", choices=["manual", "api"], help="Classification mode")
    p_setup.add_argument("--auth-file", help="Path to browser.json auth file")
    p_setup.add_argument("--non-interactive", action="store_true", help="Disable prompts")
    p_setup.add_argument(
        "--restart", action="store_true", help="Reset setup progress and start from scratch"
    )
    subparsers_by_name["setup"] = p_setup

    p_sync = sub.add_parser("sync", help="Apply incremental liked-song updates")
    add_workspace_argument(p_sync)
    add_json_argument(p_sync)
    add_dry_run_argument(p_sync)
    p_sync.add_argument("--mode", choices=["manual", "api"], help="Classification mode")
    p_sync.add_argument("--non-interactive", action="store_true", help="Disable prompts")
    subparsers_by_name["sync"] = p_sync

    p_rebuild = sub.add_parser("rebuild", help="Delete managed playlists and rebuild")
    add_workspace_argument(p_rebuild)
    add_json_argument(p_rebuild)
    add_dry_run_argument(p_rebuild)
    p_rebuild.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    p_rebuild.add_argument("--mode", choices=["manual", "api"], help="Classification mode")
    p_rebuild.add_argument("--non-interactive", action="store_true", help="Disable prompts")
    subparsers_by_name["rebuild"] = p_rebuild

    p_cleanup = sub.add_parser(
        "cleanup", help="Delete playlists managed by this tool and local managed artifacts"
    )
    add_workspace_argument(p_cleanup)
    add_json_argument(p_cleanup)
    add_dry_run_argument(p_cleanup)
    p_cleanup.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    p_cleanup.add_argument(
        "--local-only",
        action="store_true",
        help="Only remove local artifacts, keep remote playlists",
    )
    subparsers_by_name["cleanup"] = p_cleanup

    p_demo = sub.add_parser(
        "demo", help="Live setup walkthrough simulation (no auth/download/write)"
    )
    add_workspace_argument(p_demo)
    p_demo.add_argument(
        "--mode", choices=["manual", "api"], default="manual", help="Simulated classification mode"
    )
    subparsers_by_name["demo"] = p_demo

    p_stats = sub.add_parser("stats", help="Show local workspace stats and non-failing diagnostics")
    add_workspace_argument(p_stats)
    add_json_argument(p_stats)
    p_stats.add_argument(
        "--plan", help="Path to full plan JSON for diagnostics (defaults to workspace plan)"
    )
    subparsers_by_name["stats"] = p_stats
    setattr(parser, "_ytmo_subparsers", subparsers_by_name)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _base_parser(exit_on_error=False)
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    try:
        args = parser.parse_args(raw_argv)
    except argparse.ArgumentError as exc:
        _emit_scoped_parse_help(parser, raw_argv, str(exc))
        return 2
    except SystemExit as exc:
        if exc.code == 2:
            message = getattr(parser, "_ytmo_last_error", "invalid arguments")
            _emit_scoped_parse_help(parser, raw_argv, message)
            return 2
        raise

    workspace = Path(args.workspace).resolve()
    cwd = Path.cwd().resolve()
    json_output = bool(getattr(args, "json_output", False))
    ui = WizardUI()

    def emit_json(
        status: str, command: str, result: dict | None = None, error: str | None = None
    ) -> None:
        payload: dict[str, object] = {"status": status, "command": command}
        if result is not None:
            payload["result"] = result
        if error is not None:
            payload["error"] = error
        print(json.dumps(payload, ensure_ascii=False))

    if not json_output:
        _warn_legacy_root_artifacts(ui, workspace=workspace, cwd=cwd)

    try:
        if args.command == "setup":
            if not json_output:
                ui.command_header("ytmusic-organizer setup", "guided bootstrap")
            result = run_setup(
                workspace=workspace,
                auth_file=args.auth_file,
                mode=args.mode,
                interactive=not args.non_interactive,
                emit_ui=not json_output,
                restart=args.restart,
                dry_run=args.dry_run,
            )
            if json_output:
                emit_json("ok", "setup", result=result)
            else:
                if result.get("dry_run"):
                    ui.show_dry_run_summary(
                        "setup",
                        {
                            "liked_tracks": result["liked_count"],
                            "playlists_in_plan": result["playlists_in_plan"],
                            "would_create_playlists": result["would_create_playlists"],
                            "would_add_items": result["would_add_items"],
                            "missing_matches": result["missing"],
                        },
                    )
                else:
                    ui.render_recap(
                        "Setup Complete",
                        {
                            "workspace": result["workspace"],
                            "liked_tracks": result["liked_count"],
                            "status": "initial playlist build completed",
                        },
                    )
            return 0

        if args.command == "sync":
            if not json_output:
                ui.command_header("ytmusic-organizer sync", "incremental update")
            result = run_weekly_sync(
                workspace=workspace,
                mode=args.mode,
                interactive=not args.non_interactive,
                emit_ui=not json_output,
                dry_run=args.dry_run,
            )
            if json_output:
                emit_json("ok", "sync", result=result)
            elif result.get("dry_run"):
                ui.show_dry_run_summary(
                    "sync",
                    {
                        "new_likes": result["new_likes"],
                        "playlists_in_plan": result.get("playlists_in_plan", 0),
                        "would_add_items": result.get("would_add_items", 0),
                        "would_mark_processed": result.get("would_mark_processed", 0),
                        "missing_matches": result.get("missing", 0),
                    },
                )
            elif result.get("new_likes", 0) == 0:
                ui.render_callout(
                    "info",
                    "No new likes",
                    ["No new liked songs were detected in this run."],
                )
            else:
                ui.render_recap(
                    "Sync Complete",
                    {
                        "new_likes": result["new_likes"],
                        "missing_matches": result.get("missing", 0),
                    },
                )
            return 0

        if args.command == "rebuild":
            if not json_output:
                ui.command_header("ytmusic-organizer rebuild", "destructive rebuild")
            if args.non_interactive and not args.yes and not args.dry_run:
                raise RuntimeError("--yes is required when --non-interactive is set for rebuild")
            if not args.yes and not args.dry_run:
                answer = (
                    input("This will delete managed playlists and rebuild. Continue? [y/N]: ")
                    .strip()
                    .lower()
                )
                if answer not in {"y", "yes"}:
                    if json_output:
                        emit_json("cancelled", "rebuild", result={"message": "Cancelled by user"})
                    else:
                        ui.render_callout(
                            "warning", "Action cancelled", ["No changes were applied."]
                        )
                    return 1
            result = run_full_reset(
                workspace=workspace,
                mode=args.mode,
                interactive=not args.non_interactive,
                emit_ui=not json_output,
                dry_run=args.dry_run,
            )
            if json_output:
                emit_json("ok", "rebuild", result=result)
            else:
                if result.get("dry_run"):
                    ui.show_dry_run_summary(
                        "rebuild",
                        {
                            "liked_tracks": result["liked_count"],
                            "playlists_in_plan": result["playlists_in_plan"],
                            "would_delete_playlists": result["would_delete_playlists"],
                            "would_create_playlists": result["would_create_playlists"],
                            "would_add_items": result["would_add_items"],
                            "missing_matches": result["missing"],
                        },
                    )
                else:
                    ui.render_recap(
                        "Rebuild Complete",
                        {
                            "liked_tracks": result["liked_count"],
                            "deleted_playlists": result["deleted_playlists"],
                        },
                    )
                    if result.get("skipped_legacy"):
                        ui.render_callout(
                            "warning",
                            "Legacy entries skipped",
                            [", ".join(result["skipped_legacy"])],
                        )
            return 0

        if args.command == "demo":
            run_demo(
                workspace=workspace,
                mode=args.mode,
                emit_ui=not json_output,
            )
            return 0

        if args.command == "cleanup":
            if not json_output:
                ui.command_header("ytmusic-organizer cleanup", "managed resource cleanup")
            if not args.yes and not args.dry_run:
                answer = (
                    input(
                        "This will delete playlists managed by ytmusic-organizer and remove local managed files. Continue? [y/N]: "
                    )
                    .strip()
                    .lower()
                )
                if answer not in {"y", "yes"}:
                    if json_output:
                        emit_json("cancelled", "cleanup", result={"message": "Cancelled by user"})
                    else:
                        ui.render_callout(
                            "warning", "Action cancelled", ["No changes were applied."]
                        )
                    return 1
            result = run_cleanup(
                workspace=workspace, local_only=args.local_only, dry_run=args.dry_run
            )
            if json_output:
                emit_json("ok", "cleanup", result=result)
            else:
                if result.get("dry_run"):
                    ui.show_dry_run_summary(
                        "cleanup",
                        {
                            "would_delete_playlists": result["would_delete_playlists"],
                            "would_remove_local_files": result["would_remove_local_files"],
                            "local_only": result["local_only"],
                        },
                    )
                else:
                    ui.render_recap(
                        "Cleanup Complete",
                        {
                            "deleted_playlists": result["deleted_playlists"],
                            "removed_local_files": result["removed_local_files"],
                        },
                    )
                    if result.get("skipped_legacy"):
                        ui.render_callout(
                            "warning",
                            "Legacy entries skipped",
                            [", ".join(result["skipped_legacy"])],
                        )
            return 0

        if args.command == "stats":
            plan_path = Path(args.plan).resolve() if args.plan else None
            try:
                result = run_stats(workspace=workspace, plan_path=plan_path)
            except Exception as exc:
                data_dir = workspace / "data"
                result = {
                    "workspace_exists": workspace.exists(),
                    "processed_likes": 0,
                    "managed_playlists": 0,
                    "missing_matches": 0,
                    "new_likes_pending": 0,
                    "liked_snapshot_count": 0,
                    "artifact_presence": {
                        "config": (workspace / "config.toml").exists(),
                        "state": (workspace / "state.json").exists(),
                        "managed_playlists": (workspace / "managed_playlists.json").exists(),
                        "liked_songs": (data_dir / "liked_songs.json").exists(),
                        "new_likes": (data_dir / "new_likes.json").exists(),
                        "playlist_plan": (data_dir / "playlist_plan.json").exists(),
                        "new_plan": (data_dir / "new_plan.json").exists(),
                        "missing_matches": (data_dir / "missing_matches.json").exists(),
                    },
                    "plan_diagnostics": {
                        "status": "invalid_plan",
                        "plan_path": str(plan_path or (data_dir / "playlist_plan.json")),
                        "liked_path": str(data_dir / "liked_songs.json"),
                    },
                    "warnings": [f"stats runtime issue: {exc}"],
                }
            if json_output:
                emit_json("ok", "stats", result=result)
            else:
                ui.command_header("ytmusic-organizer stats", "workspace diagnostics")
                ui.show_stats(result)
            return 0

        parser.error("Unknown command")
        return 2
    except (KeyboardInterrupt, EOFError) as exc:
        if json_output:
            emit_json("error", args.command, error=build_helpful_error(exc))
        else:
            print()
            ui.render_callout(
                "warning",
                "Operation cancelled",
                build_helpful_error(exc).splitlines(),
            )
        return 1
    except Exception as exc:
        if json_output:
            emit_json("error", args.command, error=build_helpful_error(exc))
        elif "Setup was interrupted" in str(exc):
            print()
            ui.render_callout(
                "warning",
                "Setup interrupted",
                build_helpful_error(exc).splitlines(),
            )
        else:
            print(build_helpful_error(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
