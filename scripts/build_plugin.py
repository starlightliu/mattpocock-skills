from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import re


UPSTREAM = "https://github.com/mattpocock/skills.git"

PLUGIN_ROOT = Path("plugins/mattpocock-skills")
TARGET = PLUGIN_ROOT / "skills"
PLUGIN_JSON = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
UPSTREAM_FILE = PLUGIN_ROOT / "UPSTREAM"

SKILL_PREFIX = "mp-"
DISPLAY_PREFIX = "MP · "

EXCLUDED_CATEGORIES = {
    "deprecated",
    "in-progress",
}


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=True,
    )


def read_previous_upstream_commit() -> str | None:
    if not UPSTREAM_FILE.exists():
        return None

    content = UPSTREAM_FILE.read_text(encoding="utf-8")

    for line in content.splitlines():
        if line.startswith("commit="):
            return line.removeprefix("commit=").strip()

    return None


def bump_patch_version(version: str) -> str:
    parts = version.split(".")

    if len(parts) != 3:
        raise RuntimeError(
            f"Unsupported plugin version format: {version}"
        )

    major, minor, patch = parts

    try:
        patch_number = int(patch)
    except ValueError as exc:
        raise RuntimeError(
            f"Plugin patch version is not numeric: {version}"
        ) from exc

    return f"{major}.{minor}.{patch_number + 1}"


def bump_plugin_version() -> tuple[str, str]:
    if not PLUGIN_JSON.exists():
        raise RuntimeError(
            f"Plugin manifest not found: {PLUGIN_JSON}"
        )

    data = json.loads(
        PLUGIN_JSON.read_text(encoding="utf-8")
    )

    current_version = data.get("version")

    if not current_version:
        raise RuntimeError(
            "plugin.json does not contain a version"
        )

    new_version = bump_patch_version(current_version)

    data["version"] = new_version

    PLUGIN_JSON.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return current_version, new_version


def update_skill_name(
    skill_md: Path,
    target_name: str,
) -> None:
    content = skill_md.read_text(encoding="utf-8")

    new_content, replacements = re.subn(
        r"(?m)^name:\s*(.+)$",
        f"name: {target_name}",
        content,
        count=1,
    )

    if replacements != 1:
        raise RuntimeError(
            f"Could not update name in SKILL.md: {skill_md}"
        )

    skill_md.write_text(
        new_content,
        encoding="utf-8",
    )


def update_display_name(openai_yaml: Path) -> None:
    if not openai_yaml.exists():
        return

    content = openai_yaml.read_text(encoding="utf-8")

    pattern = re.compile(
        r'(?m)^(\s*display_name:\s*)["\']?(.+?)["\']?\s*$'
    )

    match = pattern.search(content)

    if not match:
        print(
            f"Warning: display_name not found in {openai_yaml}"
        )
        return

    original_display_name = match.group(2).strip()

    if original_display_name.startswith(DISPLAY_PREFIX):
        new_display_name = original_display_name
    else:
        new_display_name = (
            f"{DISPLAY_PREFIX}{original_display_name}"
        )

    new_content, replacements = pattern.subn(
        lambda m: f'{m.group(1)}"{new_display_name}"',
        content,
        count=1,
    )

    if replacements != 1:
        raise RuntimeError(
            f"Could not update display_name: {openai_yaml}"
        )

    openai_yaml.write_text(
        new_content,
        encoding="utf-8",
    )


def get_category(
    skill_dir: Path,
    source_root: Path,
) -> str | None:
    relative = skill_dir.relative_to(source_root)

    if len(relative.parts) <= 1:
        return None

    return relative.parts[0]


def main() -> None:
    previous_commit = read_previous_upstream_commit()

    with tempfile.TemporaryDirectory() as tmp:
        upstream = Path(tmp) / "upstream"

        print("Cloning upstream...")

        run(
            "git",
            "clone",
            "--depth=1",
            UPSTREAM,
            str(upstream),
        )

        source = upstream / "skills"

        if not source.exists():
            raise RuntimeError(
                f"Skills directory not found: {source}"
            )

        current_commit = run(
            "git",
            "-C",
            str(upstream),
            "rev-parse",
            "HEAD",
        ).stdout.strip()

        print(f"Previous upstream commit: {previous_commit}")
        print(f"Current upstream commit:  {current_commit}")

        # upstream 未变化：直接退出，不重建、不 bump
        if previous_commit == current_commit:
            print()
            print("Upstream has not changed.")
            print("Nothing to build.")
            return

        print()
        print("Upstream changed. Rebuilding plugin...")

        if TARGET.exists():
            shutil.rmtree(TARGET)

        TARGET.mkdir(
            parents=True,
            exist_ok=True,
        )

        skill_files = sorted(
            source.rglob("SKILL.md")
        )

        print(
            f"Found {len(skill_files)} SKILL.md files."
        )

        count = 0
        skipped = 0
        generated_names: set[str] = set()

        for source_skill_md in skill_files:
            source_skill_dir = source_skill_md.parent

            relative = source_skill_dir.relative_to(
                source
            )

            category = get_category(
                source_skill_dir,
                source,
            )

            if category in EXCLUDED_CATEGORIES:
                print(
                    f"Skip {relative}: "
                    f"excluded category '{category}'"
                )
                skipped += 1
                continue

            original_name = source_skill_dir.name
            target_name = (
                f"{SKILL_PREFIX}{original_name}"
            )

            if target_name in generated_names:
                raise RuntimeError(
                    "Duplicate skill name detected:\n"
                    f"  target: {target_name}\n"
                    f"  source: {relative}"
                )

            generated_names.add(target_name)

            target_dir = TARGET / target_name

            shutil.copytree(
                source_skill_dir,
                target_dir,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    "*.pyc",
                ),
            )

            target_skill_md = (
                target_dir / "SKILL.md"
            )

            update_skill_name(
                target_skill_md,
                target_name,
            )

            openai_yaml = (
                target_dir
                / "agents"
                / "openai.yaml"
            )

            update_display_name(
                openai_yaml
            )

            print(
                f"{relative} -> {target_name}"
            )

            count += 1

        if count == 0:
            raise RuntimeError(
                "No skills generated. "
                "Upstream structure may have changed."
            )

        old_version, new_version = bump_plugin_version()

        UPSTREAM_FILE.write_text(
            "\n".join(
                [
                    f"repo={UPSTREAM}",
                    f"commit={current_commit}",
                    f"skills={count}",
                    f"skipped={skipped}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        print()
        print(f"Generated {count} skills.")
        print(f"Skipped {skipped} skills.")
        print(
            f"Plugin version: {old_version} -> {new_version}"
        )


if __name__ == "__main__":
    main()
