from __future__ import annotations

from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
except Exception:  # pragma: no cover
    Console = None
    Panel = None


class WizardUI:
    def __init__(self) -> None:
        self._console = Console() if Console else None

    def title(self, text: str) -> None:
        if self._console and Panel:
            self._console.print(Panel.fit(text, style="bold cyan"))
            return
        print(f"\n=== {text} ===")

    def step(self, text: str) -> None:
        if self._console:
            self._console.print(f"[bold blue]>>[/bold blue] {text}")
            return
        print(f">> {text}")

    def success(self, text: str) -> None:
        if self._console:
            self._console.print(f"[bold green]OK[/bold green] {text}")
            return
        print(f"OK {text}")

    def warning(self, text: str) -> None:
        if self._console:
            self._console.print(f"[bold yellow]WARN[/bold yellow] {text}")
            return
        print(f"WARN {text}")

    def error(self, text: str) -> None:
        if self._console:
            self._console.print(f"[bold red]ERROR[/bold red] {text}")
            return
        print(f"ERROR {text}")

    def note(self, text: str) -> None:
        if self._console:
            self._console.print(text)
            return
        print(text)

    def pretty(self, value: Any) -> None:
        if self._console:
            self._console.print(value)
            return
        print(value)
