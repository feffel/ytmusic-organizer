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


def read_json_from_stdin() -> dict[str, Any]:
    while True:
        raw = sys.stdin.read()
        if not raw.strip():
            if sys.stdin.isatty():
                print("No JSON received on stdin. Paste JSON and press Ctrl-D.", file=sys.stderr)
                continue
            raise ValueError("No JSON received on stdin")
        try:
            value = _extract_json(raw)
        except Exception as exc:
            if sys.stdin.isatty():
                print(f"Invalid JSON from stdin: {exc}. Paste valid JSON and press Ctrl-D.", file=sys.stderr)
                continue
            raise ValueError(f"Invalid JSON from stdin: {exc}") from exc

        if not isinstance(value, dict):
            raise ValueError("Invalid JSON from stdin: top-level value must be an object")
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
