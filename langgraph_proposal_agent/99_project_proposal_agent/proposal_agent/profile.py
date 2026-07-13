"""Load the freelancer's profile and render it as text for prompts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_PROFILE = Path(__file__).resolve().parent.parent / "profile" / "profile.yaml"


def load_profile(path: str | Path = DEFAULT_PROFILE) -> dict[str, Any]:
    """Read profile.yaml into a dict."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def profile_to_text(profile: dict[str, Any]) -> str:
    """Render the profile as compact text to drop into a prompt."""
    lines = [
        f"Name: {profile.get('name', '')}",
        f"Title: {profile.get('title', '')}",
        f"Skills: {', '.join(profile.get('skills', []))}",
        "Projects:",
    ]
    for p in profile.get("projects", []):
        desc = " ".join(p.get("description", "").split())  # collapse whitespace
        lines.append(f"  - {p['name']} [{', '.join(p.get('tech', []))}]: {desc}")
    return "\n".join(lines)
