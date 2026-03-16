from __future__ import annotations

import sys
from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except Exception:  # pragma: no cover
    Console = None
    Panel = None
    Table = None


class WizardUI:
    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._console = Console() if (enabled and Console) else None

    def title(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console and Panel:
            self._console.print(Panel.fit(text, style="bold cyan"))
            return
        print(f"\n=== {text} ===")

    def step(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console:
            self._console.print(f"[bold blue]>>[/bold blue] {text}")
            return
        print(f">> {text}")

    def success(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console:
            self._console.print(f"[bold green]OK[/bold green] {text}")
            return
        print(f"OK {text}")

    def warning(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console:
            self._console.print(f"[bold yellow]WARN[/bold yellow] {text}")
            return
        print(f"WARN {text}")

    def error(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console:
            self._console.print(f"[bold red]ERROR[/bold red] {text}")
            return
        print(f"ERROR {text}")

    def note(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console:
            self._console.print(text)
            return
        print(text)

    def pretty(self, value: Any) -> None:
        if not self._enabled:
            return
        if self._console:
            self._console.print(value)
            return
        print(value)

    def show_stats(self, result: dict[str, Any]) -> None:
        if not self._enabled:
            return
        if self._console and Panel and Table:
            summary = Table(show_header=False, box=None, pad_edge=False)
            summary.add_column("Metric", style="bold cyan")
            summary.add_column("Value", style="bold green")
            summary.add_row("Processed likes", str(result.get("processed_likes", 0)))
            summary.add_row("Managed playlists", str(result.get("managed_playlists", 0)))
            summary.add_row("Missing matches", str(result.get("missing_matches", 0)))
            summary.add_row("Pending new likes", str(result.get("new_likes_pending", 0)))
            summary.add_row("Liked snapshot count", str(result.get("liked_snapshot_count", 0)))
            self._console.print(Panel.fit(summary, title="Workspace Metrics", border_style="bright_cyan"))

            artifact_presence = result.get("artifact_presence", {})
            artifacts = Table(show_header=True, header_style="bold magenta")
            artifacts.add_column("Artifact")
            artifacts.add_column("Status")
            ordered_keys = [
                "config",
                "state",
                "managed_playlists",
                "liked_songs",
                "new_likes",
                "playlist_plan",
                "new_plan",
                "missing_matches",
            ]
            for key in ordered_keys:
                present = bool(artifact_presence.get(key, False))
                status = "[bold green]present[/bold green]" if present else "[dim]missing[/dim]"
                artifacts.add_row(key, status)
            self._console.print(Panel.fit(artifacts, title="Artifacts", border_style="bright_blue"))
            return

        use_color = sys.stdout.isatty()

        def color(text: str, code: str) -> str:
            if not use_color:
                return text
            return f"\033[{code}m{text}\033[0m"

        def line(label: str, value: Any) -> None:
            print(f"  {color(label + ':', '36')} {color(str(value), '32')}")

        print(color("Workspace Metrics", "1;96"))
        line("Processed likes", result.get("processed_likes", 0))
        line("Managed playlists", result.get("managed_playlists", 0))
        line("Missing matches", result.get("missing_matches", 0))
        line("Pending new likes", result.get("new_likes_pending", 0))
        line("Liked snapshot count", result.get("liked_snapshot_count", 0))

        print()
        print(color("Artifacts", "1;94"))
        artifact_presence = result.get("artifact_presence", {})
        ordered_keys = [
            "config",
            "state",
            "managed_playlists",
            "liked_songs",
            "new_likes",
            "playlist_plan",
            "new_plan",
            "missing_matches",
        ]
        for key in ordered_keys:
            present = bool(artifact_presence.get(key, False))
            status = color("present", "32") if present else color("missing", "90")
            print(f"  {color(key + ':', '35')} {status}")
