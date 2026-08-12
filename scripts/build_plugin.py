from pathlib import Path
import shutil
import subprocess
import tempfile
import re

UPSTREAM = "https://github.com/mattpocock/skills.git"

PLUGIN_ROOT = Path("plugins/mattpocock-skills")
TARGET = PLUGIN_ROOT / "skills"
PREFIX = "mp-"


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

    # 获取 upstream commit，方便追踪
    commit = run(
        "git",
        "-C",
        str(upstream),
        "rev-parse",
        "HEAD",
    ).stdout.strip()

    print(f"Upstream commit: {commit}")

    # 每次全量重新生成
    if TARGET.exists():
        shutil.rmtree(TARGET)

    TARGET.mkdir(parents=True, exist_ok=True)

    count = 0

    for skill_dir in sorted(source.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_md = skill_dir / "SKILL.md"

        if not skill_md.exists():
            print(f"Skip {skill_dir.name}: SKILL.md not found")
            continue

        original_name = skill_dir.name
        target_name = f"{PREFIX}{original_name}"

        target_dir = TARGET / target_name

        shutil.copytree(
            skill_dir,
            target_dir,
            ignore=shutil.ignore_patterns(".git"),
        )

        target_skill_md = target_dir / "SKILL.md"
        content = target_skill_md.read_text(encoding="utf-8")

        # 只修改 frontmatter 中第一个 name 字段
        new_content, replacements = re.subn(
            r"(?m)^name:\s*(.+)$",
            f"name: {target_name}",
            content,
            count=1,
        )

        if replacements != 1:
            raise RuntimeError(
                f"Could not update skill name: {target_skill_md}"
            )

        target_skill_md.write_text(
            new_content,
            encoding="utf-8",
        )

        print(f"{original_name} -> {target_name}")
        count += 1

    # 保存 upstream 版本
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
