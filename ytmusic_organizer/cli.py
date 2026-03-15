from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .paths import default_workspace
from .ui import WizardUI
from .workflows import run_cleanup, run_full_reset, run_preview, run_setup, run_weekly_sync


def build_helpful_error(exc: Exception) -> str:
    text = str(exc)

    if "Auth file not found:" in text:
        return (
            f"Auth file is missing.\n"
            f"{text}\n\n"
            "How to fix:\n"
            "1. Run interactive setup (recommended):\n"
            "   ytmo setup\n"
            "   The wizard creates <workspace>/browser.json for you.\n"
            "2. If you already have a file, pass it explicitly:\n"
            "   ytmo setup --auth-file /absolute/path/to/browser.json\n"
            "3. Auth guide reference:\n"
            "   https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html"
        )

    if "Setup has not been completed" in text:
        return (
            "Setup is incomplete.\n"
            f"{text}\n\n"
            "How to fix:\n"
            "1. Run guided setup:\n"
            "   ytmo setup"
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
            "Plan JSON is invalid.\n"
            f"Validation error: {text}\n\n"
            "How to fix:\n"
            "1. Re-open the generated prompt file in your workspace data directory.\n"
            "2. Ensure model output exactly matches the expected JSON shape.\n"
            "3. Save corrected JSON and rerun."
        )

    return f"Error: {text}"


def _base_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ytmo", description="YouTube Music Organizer CLI")

    sub = parser.add_subparsers(dest="command", required=True)

    def add_workspace_argument(command_parser: argparse.ArgumentParser) -> None:
        default_path = str(default_workspace())
        command_parser.add_argument(
            "--workspace",
            default=default_path,
            help=f"Workspace directory (default: {default_path})",
        )

    p_setup = sub.add_parser("setup", help="Guided first-time setup and initial playlist build")
    add_workspace_argument(p_setup)
    p_setup.add_argument("--mode", choices=["manual", "api"], help="Classification mode")
    p_setup.add_argument("--auth-file", help="Path to browser.json auth file")
    p_setup.add_argument("--non-interactive", action="store_true", help="Disable prompts")
    p_setup.add_argument("--restart", action="store_true", help="Reset setup progress and start from scratch")

    p_sync = sub.add_parser("sync", help="Apply incremental liked-song updates")
    add_workspace_argument(p_sync)
    p_sync.add_argument("--mode", choices=["manual", "api"], help="Classification mode")

    p_reset = sub.add_parser("reset", help="Delete managed playlists and rebuild")
    add_workspace_argument(p_reset)
    p_reset.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    p_reset.add_argument("--mode", choices=["manual", "api"], help="Classification mode")

    p_cleanup = sub.add_parser("cleanup", help="Delete playlists managed by this tool and local managed artifacts")
    add_workspace_argument(p_cleanup)
    p_cleanup.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    p_cleanup.add_argument("--local-only", action="store_true", help="Only remove local artifacts, keep remote playlists")

    p_preview = sub.add_parser("preview", help="Preview matching diagnostics for a plan")
    add_workspace_argument(p_preview)
    p_preview.add_argument("--plan", help="Path to plan JSON (defaults to workspace plan)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _base_parser()
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    cwd = Path.cwd().resolve()
    ui = WizardUI()

    try:
        if args.command == "setup":
            ui.title("ytmusic-organizer setup")
            result = run_setup(
                workspace=workspace,
                cwd=cwd,
                auth_file=args.auth_file,
                mode=args.mode,
                interactive=not args.non_interactive,
                restart=args.restart,
            )
            ui.success(f"Initialized workspace at {result['workspace']}")
            ui.success("Initial playlist build completed.")
            return 0

        if args.command == "sync":
            ui.title("ytmusic-organizer sync")
            result = run_weekly_sync(workspace=workspace, cwd=cwd, mode=args.mode)
            if result.get("new_likes", 0) == 0:
                ui.warning("No new liked songs found.")
            else:
                ui.success(
                    f"Processed {result['new_likes']} new likes, "
                    f"missing matches: {result.get('missing', 0)}"
                )
            return 0

        if args.command == "reset":
            ui.title("ytmusic-organizer reset")
            if not args.yes:
                answer = input("This will delete managed playlists and rebuild. Continue? [y/N]: ").strip().lower()
                if answer not in {"y", "yes"}:
                    ui.warning("Cancelled.")
                    return 1
            result = run_full_reset(workspace=workspace, cwd=cwd, mode=args.mode)
            ui.success(
                f"Full reset completed. Liked songs: {result['liked_count']}, "
                f"deleted playlists: {result['deleted_playlists']}"
            )
            return 0

        if args.command == "preview":
            ui.title("ytmusic-organizer preview")
            plan_path = Path(args.plan).resolve() if args.plan else None
            result = run_preview(workspace=workspace, plan_path=plan_path)
            ui.pretty(
                f"Matched: {result['matched']}, missing: {result['missing']}, "
                f"loose: {result['loose']}, ambiguous: {result['ambiguous']}"
            )
            return 0

        if args.command == "cleanup":
            ui.title("ytmusic-organizer cleanup")
            if not args.yes:
                answer = input(
                    "This will delete playlists managed by ytmusic-organizer and remove local managed files. Continue? [y/N]: "
                ).strip().lower()
                if answer not in {"y", "yes"}:
                    ui.warning("Cancelled.")
                    return 1
            result = run_cleanup(workspace=workspace, cwd=cwd, local_only=args.local_only)
            ui.success(
                f"Cleanup completed. Deleted playlists: {result['deleted_playlists']}, "
                f"removed local files: {result['removed_local_files']}"
            )
            return 0

        parser.error("Unknown command")
        return 2
    except Exception as exc:
        print(build_helpful_error(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
