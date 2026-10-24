#!/usr/bin/env python3
"""Validate local Markdown links and required documentation inventory."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache", "test-results", "playwright-report", "dist"}
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
REQUIRED = [
    "AGENTS.md",
    "CLAUDE.md",
    "docs/README.md",
    "docs/implementation-roadmap.md",
    "docs/tracks/README.md",
    "backend/README.md",
    "backend/AGENTS.md",
    "backend/app/README.md",
    "backend/app/AGENTS.md",
    "backend/app/agents/README.md",
    "backend/app/agents/AGENTS.md",
    "backend/app/economy/README.md",
    "backend/app/economy/AGENTS.md",
    "backend/app/finance/README.md",
    "backend/app/finance/AGENTS.md",
    "backend/migrations/README.md",
    "backend/migrations/AGENTS.md",
    "scripts/README.md",
    "scripts/AGENTS.md",
    "frontend/README.md",
    "frontend/AGENTS.md",
]


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if not any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts)
    )


def resolve_target(source: Path, target: str) -> Path | None:
    target = unquote(target.strip("<>"))
    if not target or target.startswith(("#", "http://", "https://", "mailto:", "tel:")):
        return None
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    candidate = (source.parent / target).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None
    return candidate


def main() -> int:
    errors: list[str] = []
    for required in REQUIRED:
        if not (ROOT / required).is_file():
            errors.append(f"missing required documentation file: {required}")

    for source in markdown_files():
        text = source.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            target = match.group(1)
            resolved = resolve_target(source, target)
            if resolved is not None and not resolved.exists():
                rel_source = source.relative_to(ROOT)
                errors.append(f"{rel_source}: broken local link {target}")

    if errors:
        print("documentation check failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"documentation check passed: {len(markdown_files())} Markdown files scanned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
