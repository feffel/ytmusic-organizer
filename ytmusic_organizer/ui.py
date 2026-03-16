from __future__ import annotations

import sys
from typing import Any, Mapping

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except Exception:  # pragma: no cover
    Console = None
    Panel = None
    Table = None


class WizardUI:
    _COLOR_TITLE = "bold #ff3355"
    _COLOR_STEP = "bold #ff5f5f"
    _COLOR_SUCCESS = "bold #61d095"
    _COLOR_WARNING = "bold #ffb347"
    _COLOR_ERROR = "bold #ff6b6b"
    _BORDER_PRIMARY = "#ff3355"
    _BORDER_SECONDARY = "#ff6b6b"
    _BORDER_INFO = "#4da6ff"
    _BORDER_WARNING = "#ffb347"

    _PLAN_STATUS_LABELS = {
        "ok": "Ready",
        "skipped_missing_plan": "Needs plan file",
        "skipped_missing_liked": "Needs liked songs snapshot",
        "invalid_plan": "Plan file needs fixes",
        "invalid_liked": "Liked songs file needs fixes",
    }

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._console = Console() if (enabled and Console) else None

    def _human_plan_status(self, status: str) -> str:
        return self._PLAN_STATUS_LABELS.get(status, status)

    def title(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console and Panel:
            self._console.print(
                Panel.fit(text, border_style=self._BORDER_PRIMARY, style=self._COLOR_TITLE)
            )
            return
        print(f"\n=== {text} ===")

    def step(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console:
            self._console.print(f"[{self._COLOR_STEP}]>>[/] {text}")
            return
        print(f">> {text}")

    def success(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console:
            self._console.print(f"[{self._COLOR_SUCCESS}]OK[/] {text}")
            return
        print(f"OK {text}")

    def warning(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console:
            self._console.print(f"[{self._COLOR_WARNING}]WARN[/] {text}")
            return
        print(f"WARN {text}")

    def error(self, text: str) -> None:
        if not self._enabled:
            return
        if self._console:
            self._console.print(f"[{self._COLOR_ERROR}]ERROR[/] {text}")
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

    def show_dry_run_summary(self, command: str, fields: Mapping[str, Any]) -> None:
        if not self._enabled:
            return

        if self._console and Panel and Table:
            table = Table(show_header=False, box=None, pad_edge=False)
            table.add_column("Field", style=self._COLOR_STEP)
            table.add_column("Value", style=self._COLOR_SUCCESS)
            table.add_row("Command", command)
            for key, value in fields.items():
                table.add_row(str(key).replace("_", " ").title(), str(value))
            self._console.print(
                Panel.fit(table, title="Dry Run Summary", border_style=self._BORDER_SECONDARY)
            )
            return

        print("Dry Run Summary")
        print(f"  Command: {command}")
        for key, value in fields.items():
            print(f"  {str(key).replace('_', ' ').title()}: {value}")

    def show_stats(self, result: dict[str, Any]) -> None:
        if not self._enabled:
            return
        if self._console and Panel and Table:
            summary = Table(show_header=False, box=None, pad_edge=False)
            summary.add_column("Metric", style=self._COLOR_STEP)
            summary.add_column("Value", style=self._COLOR_SUCCESS)
            summary.add_row("Processed likes", str(result.get("processed_likes", 0)))
            summary.add_row("Managed playlists", str(result.get("managed_playlists", 0)))
            summary.add_row("Missing matches", str(result.get("missing_matches", 0)))
            summary.add_row("Pending new likes", str(result.get("new_likes_pending", 0)))
            summary.add_row("Liked snapshot count", str(result.get("liked_snapshot_count", 0)))
            diagnostics = result.get("plan_diagnostics", {})
            plan_status = self._human_plan_status(str(diagnostics.get("status", "n/a")))
            summary.add_row("Plan diagnostics", plan_status)
            self._console.print(
                Panel.fit(summary, title="Workspace Metrics", border_style=self._BORDER_PRIMARY)
            )

            artifact_presence = result.get("artifact_presence", {})
            artifacts = Table(show_header=True, header_style=self._COLOR_STEP)
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
                status = "[bold #61d095]present[/bold #61d095]" if present else "[dim]missing[/dim]"
                artifacts.add_row(key, status)
            self._console.print(
                Panel.fit(artifacts, title="Artifacts", border_style=self._BORDER_INFO)
            )

            if diagnostics.get("status") == "ok":
                diag_table = Table(show_header=False, box=None, pad_edge=False)
                diag_table.add_column("Metric", style=self._COLOR_STEP)
                diag_table.add_column("Value", style=self._COLOR_SUCCESS)
                diag_table.add_row("Matched", str(diagnostics.get("matched", 0)))
                diag_table.add_row("Missing", str(diagnostics.get("missing", 0)))
                diag_table.add_row("Loose", str(diagnostics.get("loose", 0)))
                diag_table.add_row("Ambiguous", str(diagnostics.get("ambiguous", 0)))
                self._console.print(
                    Panel.fit(
                        diag_table, title="Plan Diagnostics", border_style=self._BORDER_SECONDARY
                    )
                )

            warnings = result.get("warnings", [])
            if isinstance(warnings, list) and warnings:
                warn_table = Table(show_header=False, box=None, pad_edge=False)
                warn_table.add_column("Warning", style=self._COLOR_WARNING)
                for warning in warnings:
                    warn_table.add_row(str(warning))
                self._console.print(
                    Panel.fit(warn_table, title="Warnings", border_style=self._BORDER_WARNING)
                )
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
        diagnostics = result.get("plan_diagnostics", {})
        line("Plan diagnostics", self._human_plan_status(str(diagnostics.get("status", "n/a"))))

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

        if diagnostics.get("status") == "ok":
            print()
            print(color("Plan Diagnostics", "1;95"))
            line("Matched", diagnostics.get("matched", 0))
            line("Missing", diagnostics.get("missing", 0))
            line("Loose", diagnostics.get("loose", 0))
            line("Ambiguous", diagnostics.get("ambiguous", 0))

        warnings = result.get("warnings", [])
        if isinstance(warnings, list) and warnings:
            print()
            print(color("Warnings", "1;93"))
            for warning in warnings:
                print(f"  {color('-', '33')} {warning}")
