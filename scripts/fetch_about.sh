#!/usr/bin/env bash
# Fetch the GitHub profile README and write it as a Pelican page.
#
# Runs at build time (CI) or locally before `make html`. The output
# is committed intentionally so fresh clones and offline builds still
# render a usable About page if GitHub is unreachable.
#
# Post-processing:
#   - strips emoji / non-ASCII symbols so the page matches the rest
#     of the blog's ASCII-only convention
#   - demotes the first H1 so Pelican's page-title H1 isn't duplicated
#
# Usage: scripts/fetch_about.sh
set -euo pipefail

SRC="https://raw.githubusercontent.com/rivassec/rivassec/main/README.md"
OUT="content/pages/about.md"

mkdir -p "$(dirname "$OUT")"

BODY=$(curl -fsSL --max-time 15 "$SRC" || echo "")

if [ -z "$BODY" ]; then
  echo "scripts/fetch_about.sh: WARN - failed to fetch README from $SRC" >&2
  if [ -f "$OUT" ]; then
    echo "  keeping existing $OUT" >&2
    exit 0
  fi
  BODY=$'# Overview\n\nSee my work on [GitHub](https://github.com/rivassec).'
fi

# Strip emoji / non-ASCII and normalize em/en dashes to ASCII hyphens,
# matching the blog's ASCII-only convention. The sed below removes
# non-ASCII code points by passing the stream through `tr` first.
CLEAN=$(printf '%s' "$BODY" \
  | LC_ALL=C tr -d '\000-\010\013-\037\177' \
  | python3 -c "
import re,sys,unicodedata
text=sys.stdin.read()
text=unicodedata.normalize('NFKD',text)
text=text.replace('—','-').replace('–','-')
text=text.replace('‘','\\'').replace('’','\\'').replace('“','\"').replace('”','\"')
# Drop any remaining non-ASCII (emoji, pictographs, etc.)
text=re.sub(r'[^\x00-\x7f]+',' ',text)
# Collapse runs of whitespace that the emoji stripping can leave behind
text=re.sub(r'[ \t]+',' ',text)
# Remove trailing spaces before newline
text=re.sub(r' +\n','\n',text)
sys.stdout.write(text)
")

# Demote the first top-level H1 so Pelican's page title stays the only H1.
# Skips '---' HR lines; replaces the first line that starts with '# ' only.
CLEAN=$(printf '%s' "$CLEAN" | awk '
  BEGIN { demoted = 0 }
  /^# / && demoted == 0 { sub(/^# /, "## "); demoted = 1 }
  { print }
')

{
  echo "Title: About"
  echo "Slug: about"
  echo "Author: RivasSec"
  echo "Summary: Security engineer profile - cloud-native infrastructure security, Kubernetes and AWS IAM hardening, compliance automation."
  echo ""
  echo "$CLEAN"
} > "$OUT"

echo "scripts/fetch_about.sh: wrote $(wc -l < "$OUT") lines to $OUT"
