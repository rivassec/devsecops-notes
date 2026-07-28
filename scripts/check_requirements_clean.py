#!/usr/bin/env python3
"""Block credential/index leakage in generated requirements files.

pip-compile inlines any configured index URLs into its output. On a
machine whose global pip.conf carries a private feed URL with an
embedded credential (see: Azure Artifacts PAT near-miss, 2026-05-12 and
2026-07-27), that means one absent-minded compile can commit a secret.

Fails on any staged requirements*.txt that contains:
  - an --index-url / --extra-index-url line (this repo resolves from
    public PyPI only; a generated index line means pip config leaked in)
  - a URL with userinfo credentials (https://user:secret@host/...)
  - a pkgs.dev.azure.com reference

Run pip-compile with PIP_CONFIG_FILE=/dev/null (or `make deps`) and
this hook stays quiet.
"""
import re
import sys

PATTERNS = (
    (re.compile(r"^\s*--(extra-)?index-url\b", re.M), "index URL line (pip config leaked into output)"),
    (re.compile(r"https?://[^/\s:@]+:[^@\s]+@", re.M), "credential embedded in URL"),
    (re.compile(r"pkgs\.dev\.azure\.com", re.M), "Azure Artifacts feed reference"),
)


def main(argv: list[str]) -> int:
    rc = 0
    for path in argv:
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            print(f"::error file={path}::cannot read: {e}")
            rc = 1
            continue
        for pat, why in PATTERNS:
            m = pat.search(text)
            if m:
                line = text[: m.start()].count("\n") + 1
                print(f"::error file={path},line={line}::{why} - regenerate with PIP_CONFIG_FILE=/dev/null (make deps)")
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
