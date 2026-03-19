from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .io_utils import atomic_write_text


@dataclass(eq=True)
class Config:
    auth_file: str = "browser.json"
    classification_mode: str = "manual"
    openai_model: str = "gpt-4.1-mini"


def _to_toml(config: Config) -> str:
    return (
        "# ytmusic-organizer local config\n"
        f'auth_file = "{config.auth_file}"\n'
        f'classification_mode = "{config.classification_mode}"\n'
        f'openai_model = "{config.openai_model}"\n'
    )


def save_config(path: Path, config: Config) -> None:
    atomic_write_text(path, _to_toml(config), encoding="utf-8")


def load_or_create_config(path: Path) -> Config:
    if not path.exists():
        config = Config()
        save_config(path, config)
        return config

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError(
            f"config.toml is invalid at {path}. "
            "Fix or delete it, then rerun `ytmo setup`."
        ) from exc
    return Config(
        auth_file=str(data.get("auth_file", "browser.json")),
        classification_mode=str(data.get("classification_mode", "manual")),
        openai_model=str(data.get("openai_model", "gpt-4.1-mini")),
    )
