"""Check that every relative link and image in the repository's Markdown files points at a real file.

    python -m src.check_links

Links to websites are not fetched (they can fail for reasons outside the
project); links inside the repository must resolve, or the check fails. It
runs in CI after the pipeline, so generated documents are checked too.
"""

import re
import sys
from urllib.parse import unquote

from src.config import ROOT

LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HREF = re.compile(r"<a\s+[^>]*href=\"([^\"]+)\"")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "raw"}
EXTERNAL = ("http://", "https://", "mailto:")


def markdown_files():
    for path in sorted(ROOT.rglob("*.md")):
        if not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            yield path


def targets(text):
    # Links inside code blocks are examples, not links
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    for pattern in (LINK, HREF):
        for match in pattern.finditer(text):
            yield match.group(1)


def broken_links():
    broken = []
    for path in markdown_files():
        for target in targets(path.read_text(encoding="utf-8")):
            if target.startswith(EXTERNAL) or target.startswith("#"):
                continue
            file_part = unquote(target.split("#", 1)[0])
            if not (path.parent / file_part).resolve().exists():
                broken.append(f"{path.relative_to(ROOT).as_posix()}: {target}")
    return broken


def main():
    files = list(markdown_files())
    broken = broken_links()
    if broken:
        print("Broken links:")
        for line in broken:
            print(f"  {line}")
        sys.exit(1)
    print(f"All relative links resolve in {len(files)} Markdown files")


if __name__ == "__main__":
    main()
