from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path

    @property
    def config(self) -> Path:
        return self.root / "config.toml"

    @property
    def state(self) -> Path:
        return self.root / "state.json"

    @property
    def managed(self) -> Path:
        return self.root / "managed_playlists.json"

    @property
    def bootstrap(self) -> Path:
        return self.root / "bootstrap.json"

    @property
    def setup_state(self) -> Path:
        return self.root / "setup_state.json"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def liked_songs(self) -> Path:
        return self.data_dir / "liked_songs.json"

    @property
    def new_likes(self) -> Path:
        return self.data_dir / "new_likes.json"

    @property
    def playlist_plan(self) -> Path:
        return self.data_dir / "playlist_plan.json"

    @property
    def new_plan(self) -> Path:
        return self.data_dir / "new_plan.json"

    @property
    def missing_matches(self) -> Path:
        return self.data_dir / "missing_matches.json"


def ensure_workspace_dirs(paths: WorkspacePaths) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.data_dir.mkdir(parents=True, exist_ok=True)
