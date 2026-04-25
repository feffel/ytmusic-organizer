from __future__ import annotations

import os
import random
import re
import sys
import textwrap
import time
from typing import Any, Mapping

try:
    from rich.box import HEAVY, ROUNDED
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
except Exception:  # pragma: no cover
    Console = None
    Live = None
    Panel = None
    Table = None
    HEAVY = None
    ROUNDED = None


class WizardUI:
    _DEFAULT_MICROCOPY_PROBABILITY = 0.12
    _MICROCOPY_ENV_VARS = ("YTMO_MICROCOPY_PROBABILITY", "YTMO_MICROCOPY_PROB")
    # Fixed default palette: indigo-vinyl.
    _COLOR_TITLE = "bold #f6f8ff"
    _COLOR_ACCENT = "bold #8fb2ff"
    _COLOR_PATH = "bold #c0d0ff"
    _COLOR_INFO = "#eef1ff"
    _COLOR_SECONDARY = "#a9afc8"
    _COLOR_WARNING = "bold #d8a657"
    _COLOR_ERROR = "bold #e06c75"
    _COLOR_MUTED = "#868ead"
    _BORDER_PRIMARY = "#6f86c7"
    _BORDER_SECONDARY = "#5f6882"
    _BORDER_INFO = "#4c5670"
    _BORDER_WARNING = "#d8a657"
    _BORDER_ERROR = "#e06c75"
    _ICON_HEADER = "♪"
    _ICON_STEP = "▶"
    _ICON_DONE = "✓"
    _ICON_DETAIL = "•"
    _ICON_INFO = "♫"
    _ICON_WARNING = "!"
    _ICON_ERROR = "x"
    _WAVE_FRAMES = ("▁▂▃", "▂▃▄", "▃▄▅", "▄▅▆", "▅▆▇", "▆▇█")
    _SECTION_ICONS = {
        "Status Overview": "♪",
        "Plan & Coverage": "♬",
        "Playlist Standings": "♫",
    }

    _PLAN_STATUS_LABELS = {
        "ok": "Ready",
        "skipped_missing_plan": "Needs plan file",
        "skipped_missing_liked": "Needs liked songs snapshot",
        "invalid_plan": "Plan file needs fixes",
        "invalid_liked": "Liked songs file needs fixes",
    }
    _PATH_PATTERN = re.compile(
        r"(?P<path>(?<![:/])(?:~|/|\./|\.\./)[^\s\]\[<>{}(),;:'\"]+|[A-Za-z]:\\[^\s\]\[<>{}(),;:'\"]+)"
    )
    _MICROCOPY_BANK: dict[str, list[dict[str, Any]]] = {
        "stats_narrative": [
            {
                "text": "The algorithm still thinks in genres, and you keep proving life is messier.",
                "tones": ("music", "philosophical", "dry_sarcastic"),
            },
            {
                "text": "Identity is just repeated listening with better metadata.",
                "tones": ("music", "philosophical"),
            },
        ],
        "flow_success": [
            {
                "text": "Another clean take. No encore needed.",
                "tones": ("music", "dry_sarcastic"),
            },
            {
                "text": "Taste evolves, logs agree, everyone acts surprised.",
                "tones": ("music", "philosophical", "dry_sarcastic"),
            },
        ],
        "flow_info": [
            {
                "text": "Tiny step now, fewer regret edits later.",
                "tones": ("philosophical",),
            },
            {
                "text": "This is the part where patience outperforms speed.",
                "tones": ("philosophical", "dry_sarcastic"),
            },
        ],
        "warning_suffix": [
            {
                "text": "Good news: caution is still cheaper than cleanup.",
                "tones": ("dry_sarcastic", "philosophical"),
            },
            {
                "text": "The dramatic option remains available, just not recommended.",
                "tones": ("dry_sarcastic",),
            },
        ],
        "recap_footer": [
            {
                "text": "Same songs, better structure. Civilization advances.",
                "tones": ("music", "dry_sarcastic"),
            },
            {
                "text": "Organized chaos is still chaos, just easier to replay.",
                "tones": ("music", "philosophical"),
            },
        ],
    }

    def __init__(self, enabled: bool = True, force_tty: bool | None = None) -> None:
        self._enabled = enabled
        self._is_tty = bool(force_tty) if force_tty is not None else sys.stdout.isatty()
        self._console = Console() if (enabled and Console) else None
        self._rich_tty = bool(self._console and self._is_tty and Panel and Table)
        self._microcopy_probability = self._load_microcopy_probability()
        self._flow_total = 0
        self._flow_index = 0

    def _load_microcopy_probability(self) -> float:
        for env_var in self._MICROCOPY_ENV_VARS:
            raw = os.getenv(env_var)
            if raw is None or not raw.strip():
                continue
            try:
                value = float(raw.strip())
            except ValueError:
                break
            if value < 0.0:
                return 0.0
            if value > 1.0:
                return 1.0
            return value
        return self._DEFAULT_MICROCOPY_PROBABILITY

    def _microcopy_for_slot(self, slot: str) -> str | None:
        lines = self._MICROCOPY_BANK.get(slot, [])
        if not lines:
            return None
        if random.random() >= self._microcopy_probability:
            return None
        selected = random.choice(lines)
        return str(selected.get("text", "")).strip() or None

    def _human_plan_status(self, status: str) -> str:
        return self._PLAN_STATUS_LABELS.get(status, status)

    def _animate(self, seconds: float = 0.09) -> None:
        if self._rich_tty:
            time.sleep(seconds)

    def _wave(self) -> str:
        if self._flow_total <= 0:
            return self._WAVE_FRAMES[0]
        index = max(self._flow_index - 1, 0) % len(self._WAVE_FRAMES)
        return self._WAVE_FRAMES[index]

    def _plain_heading(self, text: str) -> None:
        print()
        print(f"[stage] {text}")

    def _style_paths(self, text: str) -> str:
        if not self._rich_tty:
            return text

        def replace(match: re.Match[str]) -> str:
            candidate = match.group("path")
            start = match.start("path")
            if "://" in candidate:
                return candidate
            if candidate.startswith("/") and start > 0:
                previous = text[start - 1]
                if previous.isalnum() or previous in "._-":
                    return candidate
            trimmed = candidate.rstrip(".,")
            suffix = candidate[len(trimmed) :]
            if not trimmed:
                return candidate
            return f"[{self._COLOR_PATH}]{trimmed}[/]{suffix}"

        return self._PATH_PATTERN.sub(replace, text)

    def _style_callout_line(self, line: str) -> str:
        if not self._rich_tty:
            return line
        styled = self._style_paths(line)
        stripped = line.strip()
        if not stripped:
            return styled
        if stripped.endswith(":"):
            return f"[bold {self._COLOR_INFO}]{styled}[/]"
        command_prefixes = ("ytmo ", "python ", "pip ", "make ", "uv ", "pytest ", "ruff ")
        if stripped.lower().startswith(command_prefixes):
            indentation = len(line) - len(line.lstrip(" "))
            return f"{' ' * indentation}[{self._COLOR_PATH}]{stripped}[/]"
        return styled

    def command_header(self, text: str, subtitle: str | None = None) -> None:
        if not self._enabled:
            return
        if self._rich_tty:
            title_text = self._style_paths(text)
            subtitle_text = self._style_paths(subtitle) if subtitle else None
            header = (
                f"{self._ICON_HEADER} {title_text}"
                if not subtitle_text
                else f"{self._ICON_HEADER} {title_text}\n[{self._COLOR_MUTED}]{subtitle_text}[/]"
            )
            self._console.print(
                Panel.fit(
                    header,
                    border_style=self._BORDER_PRIMARY,
                    style=self._COLOR_TITLE,
                    box=HEAVY,
                )
            )
            return
        self._plain_heading(text)
        if subtitle:
            print(f"  [mix] {subtitle}")

    def start_flow(self, steps: list[str] | None = None, title: str | None = None) -> None:
        if not self._enabled:
            return
        self._flow_total = len(steps or [])
        self._flow_index = 0
        if title:
            self.command_header(title)
        if self._flow_total and not self._rich_tty:
            print(f"[beat] Flow: {self._flow_total} steps")
        elif self._flow_total and self._rich_tty:
            self._console.print(
                f"[{self._COLOR_MUTED}]  {self._ICON_INFO} queue loaded: {self._flow_total} tracks[/]"
            )

    def start_step(self, text: str) -> None:
        if not self._enabled:
            return
        if self._flow_total:
            self._flow_index = min(self._flow_index + 1, self._flow_total)
            prefix = f"Step {self._flow_index}/{self._flow_total}"
        else:
            prefix = "Step"

        if self._rich_tty:
            self._console.print(
                f"[{self._COLOR_ACCENT}]{self._ICON_STEP} {prefix}[/] "
                f"[{self._COLOR_MUTED}]{self._wave()}[/] {self._style_paths(text)}"
            )
            return
        print(f"[beat] {prefix} | {text}")

    def replay_completed_step(self, text: str) -> None:
        if not self._enabled:
            return
        if self._flow_total:
            self._flow_index = min(self._flow_index + 1, self._flow_total)
            prefix = f"Step {self._flow_index}/{self._flow_total}"
        else:
            prefix = "Step"

        if self._rich_tty:
            self._console.print(
                f"[{self._COLOR_ACCENT}]{self._ICON_STEP} {prefix}[/] "
                f"[{self._COLOR_ACCENT}]{self._ICON_DONE} done[/] "
                f"[{self._COLOR_MUTED}]{self._wave()}[/] {self._style_paths(text)}"
            )
            return
        print(f"[drop] {prefix} done | {text}")

    def step_detail(self, text: str) -> None:
        if not self._enabled:
            return
        microcopy = self._microcopy_for_slot("flow_info")
        if self._rich_tty:
            detail = self._style_paths(text)
            if microcopy:
                detail = f"{detail}\n    {self._style_paths(microcopy)}"
            self._console.print(f"[{self._COLOR_MUTED}]  {self._ICON_DETAIL} {detail}[/]")
            return
        print(f"  [note] {text}")
        if microcopy:
            print(f"    {microcopy}")

    def finish_step(self, text: str) -> None:
        if not self._enabled:
            return
        microcopy = self._microcopy_for_slot("flow_success")
        if self._rich_tty:
            line = (
                f"[{self._COLOR_ACCENT}]{self._ICON_DONE} done[/] "
                f"[{self._COLOR_MUTED}]♪[/] {self._style_paths(text)}"
            )
            if microcopy:
                line = f"{line}\n[{self._COLOR_MUTED}]    {self._style_paths(microcopy)}[/]"
            self._console.print(line)
            return
        print(f"[drop] done: {text}")
        if microcopy:
            print(f"    {microcopy}")

    def finish_flow(self, text: str) -> None:
        if not self._enabled:
            return
        if self._rich_tty:
            self._console.print(
                Panel.fit(
                    self._style_paths(text),
                    border_style=self._BORDER_SECONDARY,
                    style=self._COLOR_ACCENT,
                    box=ROUNDED,
                )
            )
            return
        print(f"[encore] Flow complete: {text}")

    def render_callout(self, level: str, title: str, lines: list[str]) -> None:
        if not self._enabled:
            return

        style = self._COLOR_INFO
        border = self._BORDER_INFO
        if level == "warning":
            style = self._COLOR_WARNING
            border = self._BORDER_WARNING
        elif level == "error":
            style = self._COLOR_ERROR
            border = self._BORDER_ERROR

        icon = self._ICON_INFO
        if level == "warning":
            icon = self._ICON_WARNING
        elif level == "error":
            icon = self._ICON_ERROR

        rendered_lines = list(lines)
        if level == "warning":
            suffix = self._microcopy_for_slot("warning_suffix")
            if suffix:
                rendered_lines.append(suffix)

        if self._rich_tty:
            body = "\n".join(self._style_callout_line(line) for line in rendered_lines)
            self._console.print(
                Panel.fit(
                    body,
                    title=self._style_paths(f"{icon} {title}"),
                    border_style=border,
                    style=style,
                    box=ROUNDED,
                )
            )
            return

        self._plain_heading(title)
        for line in rendered_lines:
            print(f"  {line}")

    def render_recap(self, title: str, fields: Mapping[str, Any]) -> None:
        if not self._enabled:
            return
        microcopy = self._microcopy_for_slot("recap_footer")
        if self._rich_tty:
            table = Table(show_header=False, box=None, pad_edge=False)
            table.add_column("Field", style=self._COLOR_INFO)
            table.add_column("Value", style=self._COLOR_ACCENT)
            for key, value in fields.items():
                table.add_row(
                    str(key).replace("_", " ").title(),
                    self._style_paths(str(value)),
                )
            if microcopy:
                table.add_row("Note", self._style_paths(microcopy))
            self._console.print(
                Panel.fit(
                    table,
                    title=self._style_paths(f"{self._ICON_INFO} {title}"),
                    border_style=self._BORDER_INFO,
                    box=ROUNDED,
                )
            )
            return

        self._plain_heading(title)
        for key, value in fields.items():
            print(f"  {str(key).replace('_', ' ').title()}: {value}")
        if microcopy:
            print(f"  {microcopy}")

    def title(self, text: str) -> None:
        self.command_header(text)

    def step(self, text: str) -> None:
        self.start_step(text)

    def success(self, text: str) -> None:
        self.finish_step(text)

    def warning(self, text: str) -> None:
        self.render_callout("warning", "Caution", [text])

    def error(self, text: str) -> None:
        self.render_callout("error", "Error", [text])

    def note(self, text: str) -> None:
        self.step_detail(text)

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
        values: dict[str, Any] = {"command": command}
        values.update(fields)
        self.render_recap("Dry Run Summary", values)

    def _show_artifacts(self, artifact_presence: Mapping[str, Any]) -> None:
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
        if self._rich_tty:
            table = Table(show_header=True, header_style=self._COLOR_INFO, box=ROUNDED)
            table.add_column("Artifact")
            table.add_column("Status")
            for key in ordered_keys:
                present = bool(artifact_presence.get(key, False))
                status = (
                    f"[{self._COLOR_ACCENT}]present[/]"
                    if present
                    else f"[{self._COLOR_MUTED}]missing[/]"
                )
                table.add_row(key, status)
            self._console.print(
                Panel.fit(table, title="Artifacts", border_style=self._BORDER_INFO, box=ROUNDED)
            )
            return

        self._plain_heading("Artifacts")
        for key in ordered_keys:
            present = bool(artifact_presence.get(key, False))
            status = "present" if present else "missing"
            print(f"  {key}: {status}")

    def _stats_health_summary(
        self,
        *,
        plan_status: str,
        missing_required_artifacts: list[str],
        warnings: list[str],
    ) -> tuple[str, str]:
        if plan_status == "ok" and not missing_required_artifacts and not warnings:
            return ("Healthy", "ready for sharing")
        if plan_status == "skipped_missing_plan":
            return ("Needs plan file", "run setup/rebuild to create playlist_plan.json")
        if plan_status == "skipped_missing_liked":
            return ("Needs liked snapshot", "export liked songs to compute diagnostics")
        if plan_status in {"invalid_plan", "invalid_liked"}:
            return ("Needs fixes", "repair plan/liked artifacts and rerun stats")
        if missing_required_artifacts:
            return ("Needs setup", "core setup artifacts are incomplete")
        return (self._human_plan_status(plan_status), "review diagnostics details")

    def _stats_diagnostics_line(
        self, *, missing_required_artifacts: list[str], warnings: list[str]
    ) -> str | None:
        if not missing_required_artifacts and not warnings:
            return None
        parts: list[str] = []
        if missing_required_artifacts:
            preview = ", ".join(missing_required_artifacts[:4])
            remaining = len(missing_required_artifacts) - 4
            suffix = f" (+{remaining} more)" if remaining > 0 else ""
            parts.append(f"missing required {preview}{suffix}")
        if warnings:
            lead = warnings[0]
            clipped = f"{lead[:93]}..." if len(lead) > 96 else lead
            remaining = len(warnings) - 1
            suffix = f" (+{remaining} more)" if remaining > 0 else ""
            parts.append(f"warning {clipped}{suffix}")
        return "; ".join(parts)

    def _split_stats_podium_metrics(
        self, metrics: list[tuple[str, str, bool]]
    ) -> tuple[dict[str, dict[str, str]], list[tuple[str, str, bool]]]:
        podium: dict[str, dict[str, str]] = {
            "Gold": {},
            "Silver": {},
            "Bronze": {},
        }
        rest: list[tuple[str, str, bool]] = []
        current_medal: str | None = None
        for label, value, accented in metrics:
            if label.endswith(" podium"):
                current_medal = label.removesuffix(" podium")
                podium.setdefault(current_medal, {})["summary"] = value
                continue
            if current_medal and label == "Vibe":
                podium[current_medal]["vibe"] = value
                continue
            if current_medal and label == "Samples":
                podium[current_medal]["samples"] = value
                continue
            current_medal = None
            rest.append((label, value, accented))
        return podium, rest

    @staticmethod
    def _stats_podium_summary_parts(summary: str) -> tuple[str, str]:
        if " (" not in summary:
            return summary, ""
        name, count = summary.rsplit(" (", 1)
        return name, f"({count}"

    @staticmethod
    def _clip_cell(value: str, width: int) -> str:
        if len(value) <= width:
            return value
        if width <= 1:
            return value[:width]
        return value[: width - 1] + "…"

    @staticmethod
    def _wrap_cell(value: str, width: int) -> list[str]:
        if not value:
            return [""]
        return textwrap.wrap(
            value,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [""]

    @staticmethod
    def _wrap_list_items(items: list[str], *, width: int) -> list[str]:
        lines: list[str] = []
        current = ""
        for item in items:
            if not current:
                current = item
                continue
            candidate = f"{current}, {item}"
            if len(candidate) <= width:
                current = candidate
            else:
                lines.append(current)
                current = item
        if current:
            lines.append(current)
        return lines

    @staticmethod
    def _wrap_text(value: str, *, width: int) -> list[str]:
        return textwrap.wrap(
            value,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [""]

    def _stats_podium_cell(self, value: str, *, width: int, style: str | None) -> str:
        cell = value.ljust(width)
        if not style:
            return cell
        return f"[{style}]{cell}[/]"

    def _render_stats_podium(
        self, metrics: list[tuple[str, str, bool]], *, rich: bool
    ) -> list[str]:
        podium, rest = self._split_stats_podium_metrics(metrics)
        width = 26
        medal_order = ("Silver", "Gold", "Bronze")
        medal_titles = {
            "Silver": "SILVER #2",
            "Gold": "GOLD #1",
            "Bronze": "BRONZE #3",
        }
        medal_colors = {
            "Gold": "bold #ffd166",
            "Silver": "bold #cfd6e6",
            "Bronze": "bold #d08c60",
        }

        def row(values: list[str], *, color_headers: bool = False) -> str:
            cells: list[str] = []
            for medal, value in zip(medal_order, values, strict=True):
                style = medal_colors[medal] if rich and color_headers else None
                cells.append(self._stats_podium_cell(value, width=width, style=style))
            return "│ " + " │ ".join(cells) + " │"

        def wrapped_rows(values: list[str]) -> list[str]:
            wrapped = [self._wrap_cell(value, width) for value in values]
            height = max(len(lines) for lines in wrapped)
            rows: list[str] = []
            for idx in range(height):
                rows.append(row([lines[idx] if idx < len(lines) else "" for lines in wrapped]))
            return rows

        border = "─" * (width + 2)
        lines = [
            "┌" + "┬".join([border, border, border]) + "┐",
            row([medal_titles[medal] for medal in medal_order], color_headers=True),
        ]
        names: list[str] = []
        counts: list[str] = []
        vibes: list[str] = []
        for medal in medal_order:
            summary = podium.get(medal, {}).get("summary", "")
            name, count = self._stats_podium_summary_parts(summary)
            names.append(name)
            counts.append(count)
            vibes.append(podium.get(medal, {}).get("vibe", ""))
        lines.extend(wrapped_rows(names))
        lines.extend(wrapped_rows(counts))
        lines.extend(wrapped_rows(vibes))
        lines.extend(
            [
                "├" + "┼".join([border, border, border]) + "┤",
                row(["#2", "#1", "#3"], color_headers=True),
                "└" + "┴".join([border, border, border]) + "┘",
            ]
        )

        for medal in ("Gold", "Silver", "Bronze"):
            samples = podium.get(medal, {}).get("samples", "")
            if samples:
                sample_lines = self._wrap_text(samples, width=72)
                lines.append(f"{medal} samples: {sample_lines[0]}")
                for sample_line in sample_lines[1:]:
                    lines.append(f"  {sample_line}")

        for label, value, accented in rest:
            value_color = self._COLOR_ACCENT if accented else self._COLOR_INFO
            if label == "Honorable mentions":
                wrapped_lines = self._wrap_list_items(
                    [item.strip() for item in value.split(",") if item.strip()],
                    width=66,
                )
            elif label == "Managed playlists":
                prefix, _, names_value = value.partition(": ")
                if names_value:
                    wrapped_names = self._wrap_list_items(
                        [item.strip() for item in names_value.split(",") if item.strip()],
                        width=66,
                    )
                    wrapped_lines = [f"{prefix}: {wrapped_names[0]}"]
                    wrapped_lines.extend(wrapped_names[1:])
                else:
                    wrapped_lines = self._wrap_text(value, width=72)
            else:
                wrapped_lines = self._wrap_text(value, width=72)
            if rich:
                styled_value = self._style_paths(wrapped_lines[0])
                lines.append(
                    f"[{self._COLOR_SECONDARY}]{label}:[/] [{value_color}]{styled_value}[/]"
                )
                for wrapped_line in wrapped_lines[1:]:
                    lines.append(f"  [{value_color}]{self._style_paths(wrapped_line)}[/]")
            else:
                lines.append(f"{label}: {wrapped_lines[0]}")
                for wrapped_line in wrapped_lines[1:]:
                    lines.append(f"  {wrapped_line}")
        return lines

    def _build_stats_sections(
        self,
        *,
        identity_score: int,
        sparse: bool,
        collection_shape: str,
        managed_playlists: int,
        managed_playlist_names: list[str],
        processed_likes: int,
        plan_playlists: int,
        plan_status_raw: str,
        plan_status: str,
        coverage_ratio: float,
        top_playlists: Any,
        pending_likes: int,
        missing_matches: int,
        missing_matches_path: str | None,
        liked_snapshot: int,
        health_label: str,
        health_note: str,
        diagnostics_line: str | None,
    ) -> list[tuple[str, list[tuple[str, str, bool]]]]:
        hero: list[tuple[str, str, bool]] = [
            ("Identity score", f"{identity_score}/100", True),
            ("Overall status", f"{health_label} - {health_note}", health_label == "Healthy"),
        ]
        if diagnostics_line:
            hero.append(("Diagnostics", diagnostics_line, False))
        if not sparse:
            hero.extend(
                [
                    ("Collection shape", collection_shape, False),
                    ("Managed playlists", str(managed_playlists), True),
                    ("Processed likes", str(processed_likes), True),
                ]
            )

        shape: list[tuple[str, str, bool]] = [("Plan playlists", str(plan_playlists), True)]
        if plan_status_raw == "ok":
            shape.append(("Coverage ratio", f"{coverage_ratio:.0%}", True))
        shape.extend(
            [
                ("Plan status", plan_status, False),
            ]
        )

        highlights: list[tuple[str, str, bool]] = []
        if isinstance(top_playlists, list) and top_playlists:
            podium_labels = ("Gold podium", "Silver podium", "Bronze podium")
            podium_names: set[str] = set()
            for idx, playlist in enumerate(top_playlists[:3], start=1):
                if not isinstance(playlist, Mapping):
                    continue
                name = str(playlist.get("name", "Unnamed"))
                podium_names.add(name)
                songs = int(playlist.get("songs", 0))
                label = podium_labels[idx - 1]
                highlights.append((label, f"{name} ({songs} songs)", False))
                description = str(playlist.get("description", "")).strip()
                if description:
                    highlights.append(("Vibe", description, False))
                sample_songs = playlist.get("sample_songs", [])
                if isinstance(sample_songs, list) and sample_songs:
                    samples = "; ".join(str(song) for song in sample_songs[:3])
                    highlights.append(("Samples", samples, False))
            honorable_mentions = [
                name for name in managed_playlist_names if name and name not in podium_names
            ]
            if honorable_mentions:
                highlights.append(("Honorable mentions", ", ".join(honorable_mentions), False))
        else:
            highlights.append(("Top playlists", "No ranked playlists yet", False))
        if pending_likes > 0 or not sparse:
            highlights.append(("New likes pending", str(pending_likes), pending_likes > 0))
        if missing_matches > 0:
            highlights.append(("Missing matches", str(missing_matches), True))
            if missing_matches_path:
                highlights.append(("View missing matches", missing_matches_path, False))
        if managed_playlist_names:
            highlights.append(
                (
                    "Managed playlists",
                    f"{len(managed_playlist_names)} total: {', '.join(managed_playlist_names)}",
                    False,
                )
            )
        if liked_snapshot > 0:
            highlights.append(("Liked snapshot", str(liked_snapshot), True))

        return [
            ("Status Overview", hero),
            ("Plan & Coverage", shape),
            ("Playlist Standings", highlights),
        ]

    def _render_stats_canvas(self, sections: list[tuple[str, list[tuple[str, str, bool]]]]) -> str:
        lines: list[str] = []
        separator = f"[{self._COLOR_SECONDARY}]{'─' * 54}[/]"
        podium_colors = {
            "Gold podium": "bold #ffd166",
            "Silver podium": "bold #cfd6e6",
            "Bronze podium": "bold #d08c60",
        }
        for idx, (heading, metrics) in enumerate(sections):
            if idx:
                lines.append(separator)
            icon = self._SECTION_ICONS.get(heading, self._ICON_INFO)
            lines.append(f"[bold {self._COLOR_INFO}]{icon} {heading}[/]")
            if heading == "Playlist Standings":
                lines.extend(self._render_stats_podium(metrics, rich=True))
                continue
            for label, value, accented in metrics:
                value_color = podium_colors.get(
                    label, self._COLOR_ACCENT if accented else self._COLOR_INFO
                )
                label_color = podium_colors.get(label, self._COLOR_SECONDARY)
                styled_value = self._style_paths(value)
                lines.append(f"[{label_color}]{label}:[/] [{value_color}]{styled_value}[/]")
        return "\n".join(lines)

    def show_stats(self, result: dict[str, Any]) -> None:
        if not self._enabled:
            return

        diagnostics = result.get("plan_diagnostics", {})
        plan_status_raw = str(diagnostics.get("status", "n/a"))
        plan_status = self._human_plan_status(plan_status_raw)
        insights = result.get("insights", {})
        identity_score = int(insights.get("identity_score", 0))
        plan_playlists = int(insights.get("plan_playlists", 0))
        coverage_ratio = float(insights.get("coverage_ratio", 0.0))
        collection_shape = str(insights.get("collection_shape", "Just getting started"))
        top_playlists = insights.get("top_playlists", [])
        processed_likes = int(result.get("processed_likes", 0))
        managed_playlists = int(result.get("managed_playlists", 0))
        managed_playlist_names = [
            str(name) for name in result.get("managed_playlist_names", []) if str(name).strip()
        ]
        pending_likes = int(result.get("new_likes_pending", 0))
        missing_matches = int(result.get("missing_matches", 0))
        liked_snapshot = int(result.get("liked_snapshot_count", 0))
        warnings = [str(item) for item in result.get("warnings", []) if str(item).strip()]
        artifact_presence = result.get("artifact_presence", {})
        missing_required_artifacts = [
            str(item) for item in result.get("missing_required_artifacts", []) if str(item).strip()
        ]
        if not missing_required_artifacts:
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
        artifact_paths = result.get("artifact_paths", {})
        missing_matches_path = None
        if isinstance(artifact_paths, Mapping):
            missing_matches_path = str(artifact_paths.get("missing_matches", "")).strip() or None
        sparse = (
            identity_score == 0
            and processed_likes == 0
            and managed_playlists == 0
            and plan_playlists == 0
        )
        health_label, health_note = self._stats_health_summary(
            plan_status=plan_status_raw,
            missing_required_artifacts=missing_required_artifacts,
            warnings=warnings,
        )
        diagnostics_line = self._stats_diagnostics_line(
            missing_required_artifacts=missing_required_artifacts,
            warnings=warnings,
        )
        sections = self._build_stats_sections(
            identity_score=identity_score,
            sparse=sparse,
            collection_shape=collection_shape,
            managed_playlists=managed_playlists,
            managed_playlist_names=managed_playlist_names,
            processed_likes=processed_likes,
            plan_playlists=plan_playlists,
            plan_status_raw=plan_status_raw,
            plan_status=plan_status,
            coverage_ratio=coverage_ratio,
            top_playlists=top_playlists,
            pending_likes=pending_likes,
            missing_matches=missing_matches,
            missing_matches_path=missing_matches_path,
            liked_snapshot=liked_snapshot,
            health_label=health_label,
            health_note=health_note,
            diagnostics_line=diagnostics_line,
        )

        if self._rich_tty:
            reveal_delays = (0.25, 0.18, 0.18)
            if Live:
                seed = Panel.fit(
                    self._render_stats_canvas(sections[:1]),
                    border_style=self._BORDER_PRIMARY,
                    box=HEAVY,
                )
                with Live(
                    seed,
                    console=self._console,
                    refresh_per_second=10,
                    transient=False,
                ) as live:
                    for idx, delay in enumerate(reveal_delays):
                        frame = Panel.fit(
                            self._render_stats_canvas(sections[: idx + 1]),
                            border_style=self._BORDER_PRIMARY,
                            box=HEAVY,
                        )
                        live.update(frame, refresh=True)
                        self._animate(delay)
            else:
                self._console.print(
                    Panel.fit(
                        self._render_stats_canvas(sections),
                        border_style=self._BORDER_PRIMARY,
                        box=HEAVY,
                    )
                )
            return

        for heading, metrics in sections:
            self._plain_heading(heading)
            if heading == "Playlist Standings":
                for line in self._render_stats_podium(metrics, rich=False):
                    print(f"  {line}")
                continue
            for label, value, _ in metrics:
                print(f"  {label}: {value}")
