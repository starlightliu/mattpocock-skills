#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path


NAME_PATTERN = re.compile(r"(?m)^name:\s*(.+?)\s*$")


def prefix_skill(skill_file: Path, prefix: str) -> None:
    text = skill_file.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise ValueError(f"Missing YAML frontmatter: {skill_file}")

    closing = text.find("\n---", 3)

    if closing == -1:
        raise ValueError(f"Invalid YAML frontmatter: {skill_file}")

    frontmatter = text[:closing]
    body = text[closing:]

    match = NAME_PATTERN.search(frontmatter)

    if not match:
        raise ValueError(f"Missing name field: {skill_file}")

    old_name = match.group(1).strip().strip("\"'")
    new_name = old_name if old_name.startswith(prefix) else f"{prefix}{old_name}"

    if new_name != old_name:
        frontmatter = (
            frontmatter[: match.start()]
            + f"name: {new_name}"
            + frontmatter[match.end() :]
        )

        skill_file.write_text(frontmatter + body, encoding="utf-8")

    skill_dir = skill_file.parent

    if skill_dir.name.startswith(prefix):
        return

    target_dir = skill_dir.with_name(f"{prefix}{skill_dir.name}")

    if target_dir.exists():
        raise FileExistsError(f"Target already exists: {target_dir}")

    skill_dir.rename(target_dir)

    print(f"{old_name} -> {new_name}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: prefix-skills.py <root> <prefix>", file=sys.stderr)
        raise SystemExit(1)

    root = Path(sys.argv[1]).resolve()
    prefix = sys.argv[2]

    skill_files = list(root.rglob("SKILL.md"))

    # 优先处理更深层目录，避免父目录提前重命名
    skill_files.sort(key=lambda path: len(path.parts), reverse=True)

    for skill_file in skill_files:
        if skill_file.exists():
            prefix_skill(skill_file, prefix)


if __name__ == "__main__":
    main()
