from pathlib import Path
import shutil
import subprocess
import tempfile
import re

UPSTREAM = "https://github.com/mattpocock/skills.git"

PLUGIN_ROOT = Path("plugins/mattpocock-skills")
TARGET = PLUGIN_ROOT / "skills"
PREFIX = "mp-"

# 不发布这些分类
EXCLUDED_CATEGORIES = {
    "deprecated",
    "in-progress",
}


def run(*args):
    return subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=True,
    )


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
        raise RuntimeError(f"Skills directory not found: {source}")

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

    TARGET.mkdir(parents=True, exist_ok=True)

    count = 0

    # 递归查找所有 SKILL.md
    skill_files = sorted(source.rglob("SKILL.md"))

    print(f"Found {len(skill_files)} SKILL.md files.")

    for skill_md in skill_files:
        skill_dir = skill_md.parent

        relative = skill_dir.relative_to(source)

        # 第一层目录作为 category
        category = relative.parts[0] if len(relative.parts) > 1 else None

        if category in EXCLUDED_CATEGORIES:
            print(f"Skip {relative}: excluded category")
            continue

        original_name = skill_dir.name
        target_name = f"{PREFIX}{original_name}"

        target_dir = TARGET / target_name

        # 防止不同分类出现同名 skill
        if target_dir.exists():
            raise RuntimeError(
                f"Duplicate skill name detected: {original_name}\n"
                f"Source: {relative}"
            )

        shutil.copytree(
            skill_dir,
            target_dir,
            ignore=shutil.ignore_patterns(".git"),
        )

        target_skill_md = target_dir / "SKILL.md"

        content = target_skill_md.read_text(encoding="utf-8")

        # 只修改 frontmatter 中第一个 name
        new_content, replacements = re.subn(
            r"(?m)^name:\s*(.+)$",
            f"name: {target_name}",
            content,
            count=1,
        )

        if replacements != 1:
            raise RuntimeError(
                f"Could not update skill name: {skill_md}"
            )

        target_skill_md.write_text(
            new_content,
            encoding="utf-8",
        )

        print(
            f"{relative} -> {target_name}"
        )

        count += 1

    (PLUGIN_ROOT / "UPSTREAM").write_text(
        "\n".join(
            [
                f"repo={UPSTREAM}",
                f"commit={commit}",
                f"skills={count}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print()
    print(f"Generated {count} skills.")

    if count == 0:
        raise RuntimeError(
            "No skills generated. Upstream structure may have changed."
        )
