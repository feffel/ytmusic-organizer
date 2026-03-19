from __future__ import annotations

import json
from pathlib import Path

from .io_utils import atomic_write_text


class SetupState:
    def __init__(self, path: Path):
        self.path = path
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"completed": False, "steps": {}, "last_error": ""}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"completed": False, "steps": {}, "last_error": "invalid setup state file"}

    def _save(self) -> None:
        atomic_write_text(
            self.path,
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @property
    def completed(self) -> bool:
        return bool(self._data.get("completed"))

    def is_step_done(self, step: str) -> bool:
        steps = self._data.get("steps", {})
        return steps.get(step) == "done"

    def mark_step(self, step: str) -> None:
        steps = self._data.setdefault("steps", {})
        steps[step] = "done"
        self._save()

    def mark_error(self, message: str) -> None:
        self._data["last_error"] = message
        self._save()

    def complete(self) -> None:
        self._data["completed"] = True
        self._data["last_error"] = ""
        self._save()

    def reset(self) -> None:
        self._data = {"completed": False, "steps": {}, "last_error": ""}
        self._save()
