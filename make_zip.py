#!/usr/bin/env python3
"""Build the Claude app upload with a skill folder at the zip root."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / "skills" / "we-regret-to-inform-you"
OUT = ROOT / "we-regret-to-inform-you.zip"
FILES = ("SKILL.md", "scripts/check_facts.py", "scripts/make_docx.py",
         "scripts/score.py")
FIXED_TIME = (2026, 10, 15, 0, 0, 0)


def build(out=OUT):
    # An explicit file list excludes caches, editor files, and private run output.
    # Stored entries also avoid differences between zlib versions and platforms.
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(FILES):
            info = zipfile.ZipInfo(f"we-regret-to-inform-you/{name}", FIXED_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (SKILL / name).read_bytes())
    return Path(out)


if __name__ == "__main__":
    print(build())
