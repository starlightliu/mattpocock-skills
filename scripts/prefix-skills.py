#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


NAME_PATTERN = re.compile(
    r"(?m)^name:\s*([^\n]+)"
)


DISPLAY_NAME_PATTERN = re.compile(
    r'("display_name"\s*:\s*")([^"]+)(")'
)


def normalize_prefix(prefix: str) -> str:

    if not prefix.endswith("-"):
        prefix += "-"

    return prefix


def prefix_name(
    name: str,
    prefix: str
) -> str:

    if name.startswith(prefix):
        return name

    return f"{prefix}{name}"


def prefix_display_name(
    name: str,
    prefix: str
) -> str:

    display_prefix = (
        prefix
        .rstrip("-")
        .upper()
    )

    if name.startswith(display_prefix + " "):
        return name

    return f"{display_prefix} {name}"


#
# -----------------------------
# SKILL.md 处理
# -----------------------------
#

def update_skill_md(
    skill_file: Path,
    prefix: str
) -> str | None:


    text = skill_file.read_text(
        encoding="utf-8"
    )

    old_text = text


    skill_name = None


    match = NAME_PATTERN.search(text)


    if match:

        old_name = (
            match.group(1)
            .strip()
            .strip("\"'")
        )

        new_name = prefix_name(
            old_name,
            prefix
        )

        skill_name = new_name


        if old_name != new_name:

            text = (
                text[:match.start(1)]
                + new_name
                + text[match.end(1):]
            )


    if text != old_text:

        skill_file.write_text(
            text,
            encoding="utf-8"
        )


    return skill_name



#
# -----------------------------
# plugin.json / json metadata
# -----------------------------
#

def update_json_metadata(
    json_file: Path,
    prefix: str
):

    try:

        data = json.loads(
            json_file.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        return


    changed = False


    def walk(obj):

        nonlocal changed


        if isinstance(obj, dict):

            for key, value in obj.items():

                if key == "display_name" and isinstance(value, str):

                    new_value = prefix_display_name(
                        value,
                        prefix
                    )

                    if new_value != value:

                        obj[key] = new_value
                        changed = True


                else:

                    walk(value)


        elif isinstance(obj, list):

            for item in obj:

                walk(item)


    walk(data)


    if changed:

        json_file.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            )
            + "\n",
            encoding="utf-8"
        )

        print(
            f"updated metadata: {json_file}"
        )



#
# -----------------------------
# directory rename
# -----------------------------
#

def collect_directory_rename(
    skill_file: Path,
    prefix: str
):

    skill_dir = skill_file.parent


    old_name = skill_dir.name


    if old_name.startswith(prefix):

        return None


    new_name = f"{prefix}{old_name}"


    return (
        skill_dir,
        skill_dir.parent / new_name
    )



def apply_directory_rename(
    rename_pairs
):

    #
    # 深层目录优先
    #
    rename_pairs.sort(
        key=lambda x: len(x[0].parts),
        reverse=True
    )


    for old, new in rename_pairs:


        if not old.exists():

            continue


        if new.exists():

            raise RuntimeError(
                f"Target exists: {new}"
            )


        old.rename(new)


        print(
            f"rename: {old.name} -> {new.name}"
        )



#
# -----------------------------
# main
# -----------------------------
#

def main():

    if len(sys.argv) != 3:

        print(
            "Usage: prefix-skills.py <repo-root> <prefix>",
            file=sys.stderr
        )

        sys.exit(1)



    root = Path(
        sys.argv[1]
    ).resolve()


    prefix = normalize_prefix(
        sys.argv[2]
    )


    #
    # 1. 修改所有 SKILL.md
    #
    skill_files = list(
        root.rglob("SKILL.md")
    )


    rename_pairs = []


    for skill_file in skill_files:


        print(
            f"process skill: {skill_file}"
        )


        update_skill_md(
            skill_file,
            prefix
        )


        pair = collect_directory_rename(
            skill_file,
            prefix
        )


        if pair:

            rename_pairs.append(pair)



    #
    # 2. 修改所有 JSON metadata
    #
    json_files = list(
        root.rglob("*.json")
    )


    for json_file in json_files:

        update_json_metadata(
            json_file,
            prefix
        )



    #
    # 3. 最后统一 rename
    #
    apply_directory_rename(
        rename_pairs
    )



if __name__ == "__main__":

    main()
