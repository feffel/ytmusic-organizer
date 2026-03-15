from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
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


def wait_for_json_file(path: Path, poll_seconds: int = 3) -> dict[str, Any]:
    while True:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        time.sleep(poll_seconds)


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
