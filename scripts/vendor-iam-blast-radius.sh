#!/usr/bin/env bash
# Re-sync the vendored IAM Blast Radius web build from the secure-iam-lint repo.
# The blog only SERVES this tool; its source of truth is rivassec/secure-iam-lint.
# Usage: scripts/vendor-iam-blast-radius.sh [path-to-secure-iam-lint-clone]
set -euo pipefail
SRC="${1:-$HOME/dev/secure-iam-lint}"
DEST="content/tools/iam-blast-radius"
[ -d "$SRC/content/tools/iam-blast-radius" ] || { echo "not a secure-iam-lint clone: $SRC" >&2; exit 1; }
SHA=$(git -C "$SRC" rev-parse HEAD)
# Mirror the served web files (engine + shell); keep the local vendor marker.
rsync -a --delete --exclude VENDORED.md "$SRC/content/tools/iam-blast-radius/" "$DEST/"
sed -i '' "s|Pinned commit: .*|Pinned commit: $SHA|" "$DEST/VENDORED.md" 2>/dev/null \
  || sed -i "s|Pinned commit: .*|Pinned commit: $SHA|" "$DEST/VENDORED.md"
echo "synced $DEST from secure-iam-lint@$SHA"
