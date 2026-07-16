#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from pathlib import Path


def normalize_prefix(prefix: str) -> str:
    prefix = prefix.strip()

    if not prefix:
        raise ValueError("Prefix cannot be empty")

    if not prefix.endswith("-"):
        prefix += "-"

    return prefix


def get_display_prefix(prefix: str) -> str:
    return prefix.rstrip("-").upper()


def prefix_skill_name(name: str, prefix: str) -> str:
    if name.startswith(prefix):
        return name

    return f"{prefix}{name}"


def prefix_display_name(name: str, prefix: str) -> str:
    display_prefix = get_display_prefix(prefix)

    if name == display_prefix:
        return name

    if name.startswith(f"{display_prefix} "):
        return name

    return f"{display_prefix} {name}"


def replace_yaml_scalar(
    text: str,
    key: str,
    transform: Callable[[str], str],
    *,
    count: int = 0,
) -> tuple[str, int]:
    """
    Replace a simple YAML scalar while preserving indentation and quotes.

    Examples:

        name: ask-matt
        name: "ask-matt"
        display_name: "Ask Matt"
    """

    pattern = re.compile(
        rf"^(?P<head>[ \t]*{re.escape(key)}:[ \t]*)"
        rf"(?P<value>[^\r\n]*)"
        rf"(?P<newline>\r?\n?)$",
        re.MULTILINE,
    )

    replacements = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal replacements

        raw_value = match.group("value")

        value_without_trailing_space = raw_value.rstrip(" \t")
        trailing_space = raw_value[len(value_without_trailing_space) :]

        scalar = value_without_trailing_space.strip()

        if not scalar:
            return match.group(0)

        quote = ""
        value = scalar

        if (
            len(scalar) >= 2
            and scalar[0] in {'"', "'"}
            and scalar[-1] == scalar[0]
        ):
            quote = scalar[0]
            value = scalar[1:-1]

        new_value = transform(value)

        if new_value == value:
            return match.group(0)

        replacements += 1

        if quote:
            rendered_value = f"{quote}{new_value}{quote}"
        else:
            rendered_value = new_value

        return (
            f"{match.group('head')}"
            f"{rendered_value}"
            f"{trailing_space}"
            f"{match.group('newline')}"
        )

    updated_text = pattern.sub(
        replace,
        text,
        count=count,
    )

    return updated_text, replacements


def update_skill_md(
    skill_file: Path,
    prefix: str,
) -> None:
    text = skill_file.read_text(encoding="utf-8")

    updated_text, replacements = replace_yaml_scalar(
        text,
        "name",
        lambda value: prefix_skill_name(value, prefix),
        count=1,
    )

    if replacements == 0:
        current_name_pattern = re.compile(
            rf"(?m)^[ \t]*name:[ \t]*"
            rf'["\']?{re.escape(prefix)}'
        )

        if not current_name_pattern.search(text):
            raise ValueError(
                f"Could not update name in {skill_file}"
            )

        return

    skill_file.write_text(
        updated_text,
        encoding="utf-8",
    )

    print(f"updated skill name: {skill_file}")


def update_openai_yaml(
    metadata_file: Path,
    prefix: str,
) -> None:
    text = metadata_file.read_text(encoding="utf-8")

    updated_text, replacements = replace_yaml_scalar(
        text,
        "display_name",
        lambda value: prefix_display_name(value, prefix),
        count=1,
    )

    if replacements == 0:
        display_prefix = get_display_prefix(prefix)

        prefixed_pattern = re.compile(
            rf"(?m)^[ \t]*display_name:[ \t]*"
            rf'["\']?{re.escape(display_prefix)}(?:[ \t]|["\']?$)'
        )

        if not prefixed_pattern.search(text):
            raise ValueError(
                f"Could not update display_name in {metadata_file}"
            )

        return

    metadata_file.write_text(
        updated_text,
        encoding="utf-8",
    )

    print(f"updated display name: {metadata_file}")


def collect_directory_rename(
    skill_dir: Path,
    prefix: str,
) -> tuple[Path, Path] | None:
    old_name = skill_dir.name

    if old_name.startswith(prefix):
        return None

    target_dir = skill_dir.with_name(
        f"{prefix}{old_name}"
    )

    return skill_dir, target_dir


def apply_directory_renames(
    rename_pairs: list[tuple[Path, Path]],
) -> None:
    unique_pairs = {
        old_dir: new_dir
        for old_dir, new_dir in rename_pairs
    }

    ordered_pairs = sorted(
        unique_pairs.items(),
        key=lambda pair: len(pair[0].parts),
        reverse=True,
    )

    for old_dir, new_dir in ordered_pairs:
        if not old_dir.exists():
            raise FileNotFoundError(
                f"Source directory does not exist: {old_dir}"
            )

        if new_dir.exists():
            raise FileExistsError(
                f"Target directory already exists: {new_dir}"
            )

        old_dir.rename(new_dir)

        print(
            f"renamed directory: "
            f"{old_dir.name} -> {new_dir.name}"
        )


def resolve_skills_root(root: Path) -> Path:
    repository_skills_root = root / "skills"

    if repository_skills_root.is_dir():
        return repository_skills_root

    if root.name == "skills" and root.is_dir():
        return root

    raise FileNotFoundError(
        f"Skills directory not found under {root}"
    )


def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Usage: prefix-skills.py <repo-root> <prefix>",
            file=sys.stderr,
        )
        raise SystemExit(1)

    root = Path(sys.argv[1]).resolve()
    prefix = normalize_prefix(sys.argv[2])

    if not root.is_dir():
        raise NotADirectoryError(
            f"Repository root does not exist: {root}"
        )

    skills_root = resolve_skills_root(root)

    skill_files = sorted(
        skills_root.rglob("SKILL.md")
    )

    if not skill_files:
        raise FileNotFoundError(
            f"No SKILL.md files found under {skills_root}"
        )

    rename_pairs: list[tuple[Path, Path]] = []
    metadata_count = 0

    for skill_file in skill_files:
        skill_dir = skill_file.parent

        update_skill_md(
            skill_file,
            prefix,
        )

        metadata_file = (
            skill_dir
            / "agents"
            / "openai.yaml"
        )

        if metadata_file.is_file():
            update_openai_yaml(
                metadata_file,
                prefix,
            )

            metadata_count += 1

        rename_pair = collect_directory_rename(
            skill_dir,
            prefix,
        )

        if rename_pair is not None:
            rename_pairs.append(rename_pair)

    apply_directory_renames(rename_pairs)

    print()
    print(f"processed skills: {len(skill_files)}")
    print(f"processed openai metadata: {metadata_count}")
    print(f"directory renames: {len(rename_pairs)}")


if __name__ == "__main__":
    main()
