# devsecops-notes conventions

Project-specific rules for future Claude sessions working on this repo.

## Commit identity

All commits must be authored as `rivassec <rivassec@rivassec.com>`. This machine's default git config is `oliver.rivas@primer.ai` (the work identity), so always override on each commit:

```bash
GIT_AUTHOR_NAME=rivassec \
GIT_AUTHOR_EMAIL=rivassec@rivassec.com \
GIT_COMMITTER_NAME=rivassec \
GIT_COMMITTER_EMAIL=rivassec@rivassec.com \
git commit -m "..."
```

## Pushing to origin

SSH pushes need the personal key, not the default:

```bash
GIT_SSH_COMMAND="ssh -i ~/.ssh/git_rivassec -o IdentitiesOnly=yes" git push
```

## Opening PRs

The `gh` CLI is logged in as both `oliveratprimer` (default) and `rivassec`. Switch before creating PRs so the author attribution is correct:

```bash
gh auth switch --user rivassec
gh pr create ...
gh auth switch --user oliveratprimer   # switch back when done
```

## Pip dependency workflow

`requirements.in` is the human-edited source. `requirements.txt` is generated with `--generate-hashes`. CI runs `pip install --require-hashes -r requirements.txt`, so any `requirements.txt` edit that doesn't come from `pip-compile` breaks the build.

**Always set `PIP_CONFIG_FILE=/dev/null` when running pip-compile.** This machine's global pip config has a Primer Azure Artifacts `--extra-index-url` with an embedded PAT; without the override, pip-compile inlines that URL (including the secret) into `requirements.txt` and GitHub push-protection blocks the push. Full regen:

```bash
python3.13 -m venv .venv-compile
PIP_CONFIG_FILE=/dev/null .venv-compile/bin/pip install -q pip-tools
PIP_CONFIG_FILE=/dev/null .venv-compile/bin/pip-compile \
  --generate-hashes --output-file=requirements.txt requirements.in
rm -rf .venv-compile
# Scan before committing:
grep -E "pkgs\.dev\.azure|primer20260114" requirements.txt && echo "SECRET LEAKED, DO NOT COMMIT"
```

Dependabot bumps `requirements.in` weekly. Its PRs require a local pip-compile pass before merging - Dependabot can't run pip-compile on our behalf.

## Building and previewing locally

```bash
.venv/bin/pelican content -s pelicanconf.py -o /tmp/dev      # dev build (relative URLs)
.venv/bin/pelican content -s publishconf.py -o /tmp/prod     # prod build (absolute URLs)
make serve                                                   # serve dev build at :8000
```

## Cover image generation

`scripts/generate_covers.py` renders 1200x630 PNGs per post via Pillow. Fonts (Inter v4.1 OFL) are vendored under `scripts/fonts/`. Run locally, commit the outputs:

```bash
.venv/bin/python scripts/generate_covers.py                   # missing only
.venv/bin/python scripts/generate_covers.py --force           # regenerate all
.venv/bin/python scripts/generate_covers.py --only <slug>     # one post
.venv/bin/python scripts/generate_covers.py --write-frontmatter  # insert Cover: line
```

Each cover derives only from Title + Category, so re-run after changing either.

## SEO wiring (already in place, don't duplicate)

- Per-article meta description <- `Summary:` frontmatter. Aim for 150-160 chars.
- Per-article OG image <- `Cover:` frontmatter, with fallback chain `article.cover -> OG_IMAGE -> SITELOGO`.
- Twitter Cards emitted site-wide in `themes/Flex/templates/partial/og.html` and per-article in `og_article.html`.
- JSON-LD `BlogPosting` rendered on article pages via `partial/jsonld_article.html`. Image chain mirrors OG.
- `Modified:` frontmatter on every post drives `article:modified_time`, JSON-LD `dateModified`, and sitemap `<lastmod>`. Bump it when editing a post.
- Internal cross-links use `{filename}other-post.md` syntax. Lychee fails the CI build on broken links (internal or external).

## CI overview

Single workflow: `.github/workflows/deploy.yml`. Triggers on `push` to main (build + deploy) and `pull_request` to main (build + lychee link-check, no deploy). Dependencies install with `--require-hashes`. Deploys to `gh-pages`, served at rivassec.com.

## Site is live at rivassec.com

Production branch is `gh-pages` (derived artifact, force-pushed on every main deploy). Don't treat `gh-pages` as a source-of-truth branch.

## Skipped intentionally

- PR preview deployments: not worth the complexity for a single-author blog with link-checker and CI build coverage.
- Submodule teardown warning: cosmetic only; fixes require disproportionate scope (vendoring plugins, committing to upstream).
