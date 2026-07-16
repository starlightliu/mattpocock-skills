#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path


NAME_PATTERN = re.compile(
    r"(?m)^name:\s*([^\n]+)"
)

DISPLAY_NAME_PATTERN = re.compile(
    r'(?m)^(\s*display_name:\s*["\']?)(.+?)(["\']?\s*)$'
)


def add_name_prefix(name: str, prefix: str) -> str:
    """
    Add prefix to skill name.

    example:
      ask-matt -> mp-ask-matt
      mp-ask-matt -> mp-ask-matt
    """

    if name.startswith(prefix):
        return name

    return f"{prefix}{name}"


def add_display_prefix(display_name: str, prefix: str) -> str:
    """
    Add display prefix.

    example:
      Ask Matt -> MP Ask Matt
      MP Ask Matt -> MP Ask Matt
    """

    display_prefix = prefix.rstrip("-").upper()

    if display_name.startswith(display_prefix + " "):
        return display_name

    return f"{display_prefix} {display_name}"


def update_skill_metadata(
    skill_file: Path,
    prefix: str,
) -> str:

    text = skill_file.read_text(
        encoding="utf-8"
    )

    old_text = text

    #
    # update name:
    #
    # name: ask-matt
    #
    name_match = NAME_PATTERN.search(text)

    old_name = None
    new_name = None

    if name_match:

        old_name = (
            name_match.group(1)
            .strip()
            .strip('"\'')
        )

        new_name = add_name_prefix(
            old_name,
            prefix
        )

        if old_name != new_name:

            text = (
                text[:name_match.start(1)]
                + new_name
                + text[name_match.end(1):]
            )


    #
    # update display_name:
    #
    # display_name: "Ask Matt"
    #
    display_match = DISPLAY_NAME_PATTERN.search(text)

    if display_match:

        old_display = (
            display_match.group(2)
            .strip()
        )

        new_display = add_display_prefix(
            old_display,
            prefix
        )

        if old_display != new_display:

            text = (
                text[:display_match.start(2)]
                + new_display
                + text[display_match.end(2):]
            )


    if text != old_text:

        skill_file.write_text(
            text,
            encoding="utf-8"
        )


    return new_name or old_name or skill_file.parent.name


def rename_skill_directory(
    skill_file: Path,
    prefix: str,
):

    skill_dir = skill_file.parent

    old_dir_name = skill_dir.name

    if old_dir_name.startswith(prefix):
        return

    new_dir_name = f"{prefix}{old_dir_name}"

    target = skill_dir.parent / new_dir_name

    if target.exists():
        raise FileExistsError(
            f"Target directory exists: {target}"
        )

    skill_dir.rename(target)

    print(
        f"rename: {old_dir_name} -> {new_dir_name}"
    )


def process_skill(
    skill_file: Path,
    prefix: str,
):

    name = update_skill_metadata(
        skill_file,
        prefix
    )

    rename_skill_directory(
        skill_file,
        prefix
    )

    print(
        f"processed: {name}"
    )


def main():

    if len(sys.argv) != 3:

        print(
            "Usage: prefix-skills.py <skills-root> <prefix>",
            file=sys.stderr
        )

        sys.exit(1)


    root = Path(
        sys.argv[1]
    ).resolve()

    prefix = sys.argv[2]


    if not prefix.endswith("-"):
        prefix += "-"


    skill_files = list(
        root.rglob("SKILL.md")
    )


    #
    # 先处理深层目录
    # 避免父目录 rename 后路径失效
    #
    skill_files.sort(
        key=lambda x: len(x.parts),
        reverse=True
    )


    for skill_file in skill_files:

        try:

            process_skill(
                skill_file,
                prefix
            )

        except Exception as e:

            print(
                f"ERROR: {skill_file}: {e}",
                file=sys.stderr
            )

            raise


if __name__ == "__main__":
    main()
