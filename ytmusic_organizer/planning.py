from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

from openai import OpenAI


def _extract_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))

    raise ValueError("Could not parse JSON from model response")


def _read_interactive_json_candidate() -> str:
    lines: list[str] = []
    mode: str | None = None

    while True:
        try:
            line = input()
        except EOFError:
            return "\n".join(lines)

        stripped = line.strip()
        if mode is None:
            if not stripped:
                continue
            lines.append(line)
            mode = "json" if stripped.startswith("{") or stripped.startswith("[") else "raw"
        elif mode == "raw":
            if not stripped:
                return "\n".join(lines)
            lines.append(line)
        else:
            lines.append(line)
            if not stripped:
                return "\n".join(lines)

        candidate = "\n".join(lines)
        try:
            _extract_json(candidate)
            return candidate
        except Exception:
            continue


def read_json_from_stdin() -> dict[str, Any]:
    interactive = sys.stdin.isatty()

    while True:
        raw = _read_interactive_json_candidate() if interactive else sys.stdin.read()
        if not raw.strip():
            if interactive:
                print(
                    "No JSON received. Paste JSON and press Enter (use a blank line if needed).",
                    file=sys.stderr,
                )
                continue
            raise ValueError("No JSON received")
        try:
            value = _extract_json(raw)
        except Exception as exc:
            if interactive:
                print(
                    f"Invalid JSON input: {exc}. Paste valid JSON and try again.",
                    file=sys.stderr,
                )
                continue
            raise ValueError(f"Invalid JSON input: {exc}") from exc

        if not isinstance(value, dict):
            if interactive:
                print(
                    "Invalid JSON input: top-level value must be an object. Paste valid JSON and try again.",
                    file=sys.stderr,
                )
                continue
            raise ValueError("Invalid JSON input: top-level value must be an object")
        return value


def render_prompt(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def classify_with_openai(prompt: str, model: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for --mode api")

    client = OpenAI(api_key=api_key)
    response = client.responses.create(model=model, input=prompt)
    return _extract_json(response.output_text)
