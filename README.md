# DevSecOps Notes

Source for [rivassec.com](https://rivassec.com), a blog on infrastructure security, Kubernetes, IAM, cloud hardening, and OSINT by RivasSec.

## Stack

- [Pelican](https://getpelican.com/) static site generator (config in `pelicanconf.py` and `publishconf.py`)
- [Flex](https://github.com/alexandrevicenzi/Flex) theme, vendored under `themes/Flex/` with local edits
- Pelican plugins vendored under `plugins/` (sitemap, neighbors, post_stats, related_posts, extract_toc)
- Markdown posts in `content/`
- Self-hosted fonts (Source Sans 3, Source Code Pro) under `content/static/fonts/`
- CI + deploy via GitHub Actions to `gh-pages` branch (`.github/workflows/deploy.yml`)

## Local development

```bash
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.txt
.venv/bin/pelican content -s pelicanconf.py -o output   # dev build (relative URLs)
.venv/bin/pelican content -s publishconf.py -o output   # prod build (absolute URLs)
make serve                                              # serves output/ on :8000
```

`pelicanconf.py` is the dev config, `publishconf.py` extends it for production.

## Dependency management

`requirements.in` is the source of truth (hand-edited). `requirements.txt` is generated with `pip-compile --generate-hashes` and enforced via `pip install --require-hashes` in CI. To regenerate after editing `.in`:

```bash
python3.13 -m venv .venv-compile
PIP_CONFIG_FILE=/dev/null .venv-compile/bin/pip install pip-tools
PIP_CONFIG_FILE=/dev/null .venv-compile/bin/pip-compile \
    --generate-hashes --output-file=requirements.txt requirements.in
```

Dependabot opens weekly PRs bumping `requirements.in`; each needs a local pip-compile pass before merging.

CI installs with `pip install --require-hashes --no-deps -r requirements.txt`. The `--no-deps` flag is intentional: when an upstream like Pelican hard-pins a transitive (e.g. `Pygments<2.20.0`), we sometimes need to override that pin to patch a security advisory. Every transitive is already pinned with hashes in `requirements.txt`, so `--no-deps` is safe and the lockfile stays authoritative.

## Cover image generation

Per-article 1200x630 social cards are rendered from Title + Category:

```bash
.venv/bin/python scripts/generate_covers.py                   # generate missing
.venv/bin/python scripts/generate_covers.py --force           # regenerate all
.venv/bin/python scripts/generate_covers.py --only <slug>     # single post
.venv/bin/python scripts/generate_covers.py --write-frontmatter  # insert Cover: line
```

Inter v4.1 fonts are vendored under `scripts/cover_fonts/`. Requires `pngquant` on PATH for compression; warns otherwise.

## Deploy

CI builds on every PR to `main` (lychee link-check, Pelican build) and deploys to `gh-pages` on pushes to `main`. No manual deploy required.

## License

Content (c) RivasSec. Code fragments and configuration are permissive; see `LICENSE`. Vendored fonts ship under the SIL Open Font License - see `scripts/fonts/LICENSE.txt` and `content/static/fonts/LICENSE-*.txt`.
