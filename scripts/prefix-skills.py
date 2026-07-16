#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


def prefix_display_name(
    value: str,
    prefix: str
) -> str:

    prefix = prefix.upper()

    if value.startswith(prefix + " "):
        return value

    return f"{prefix} {value}"


def process(
    file: Path,
    prefix: str
):

    data = json.loads(
        file.read_text(
            encoding="utf-8"
        )
    )

    changed = False


    interface = data.get(
        "interface"
    )


    if interface:

        display_name = interface.get(
            "display_name"
        )

        if display_name:

            new_name = prefix_display_name(
                display_name,
                prefix
            )

            if new_name != display_name:

                interface["display_name"] = new_name
                changed = True


    if changed:

        file.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            ) + "\n",
            encoding="utf-8"
        )

        print(
            f"updated {file}"
        )


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print(
            "Usage: prefix-plugin.py <plugin.json> <prefix>"
        )
        sys.exit(1)


    process(
        Path(sys.argv[1]),
        sys.argv[2]
    )
