from pathlib import Path
import shutil
import subprocess
import tempfile
import re


UPSTREAM = "https://github.com/mattpocock/skills.git"

PLUGIN_ROOT = Path("plugins/mattpocock-skills")
TARGET = PLUGIN_ROOT / "skills"

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


def update_skill_name(skill_md: Path, target_name: str) -> None:
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

    # 避免重复添加前缀
    if original_display_name.startswith(DISPLAY_PREFIX):
        new_display_name = original_display_name
    else:
        new_display_name = (
            f"{DISPLAY_PREFIX}{original_display_name}"
        )

    new_content, replacements = pattern.subn(
        lambda m: (
            f'{m.group(1)}"{new_display_name}"'
        ),
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

        commit = run(
            "git",
            "-C",
            str(upstream),
            "rev-parse",
            "HEAD",
        ).stdout.strip()

        print(f"Upstream commit: {commit}")

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
                f"{relative} "
                f"-> {target_name}"
            )

            count += 1

        if count == 0:
            raise RuntimeError(
                "No skills generated. "
                "Upstream structure may have changed."
            )

        upstream_file = (
            PLUGIN_ROOT / "UPSTREAM"
        )

        upstream_file.write_text(
            "\n".join(
                [
                    f"repo={UPSTREAM}",
                    f"commit={commit}",
                    f"skills={count}",
                    f"skipped={skipped}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        print()
        print(
            f"Generated {count} skills."
        )
        print(
            f"Skipped {skipped} skills."
        )


if __name__ == "__main__":
    main()
