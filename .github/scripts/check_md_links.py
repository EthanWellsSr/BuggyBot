#!/usr/bin/env python3
"""CI check: every relative link in a tracked Markdown file points to a file or
folder that exists. Web links (http, https, mailto) and same-page anchors are
skipped, so the check needs no network access.

Links are written with %20 for spaces (e.g. Model%20Training/README.md); they
are decoded before checking. A #section suffix is ignored.
"""
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parents[2]
# [text](target) and [text](target "title"); images ![alt](target) match too.
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def main():
    files = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=REPO,
                           capture_output=True, text=True, check=True).stdout.split("\0")
    broken = []
    for name in filter(None, files):
        md = REPO / name
        in_code = False
        for lineno, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_code = not in_code  # links inside code blocks are examples, not links
                continue
            if in_code:
                continue
            for target in LINK.findall(line):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path = unquote(target.split("#", 1)[0])
                if path and not (md.parent / path).exists():
                    broken.append(f"{name}:{lineno}: {target}")
    for b in broken:
        print(f"  broken link: {b}")
    print(f"Checked {len([f for f in files if f])} Markdown files; {len(broken)} broken links.")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
