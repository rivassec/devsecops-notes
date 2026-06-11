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

## Anonymization (mandatory before publish)

Every post must be scrubbed of work-identifying detail before merge. The blog is a personal artifact; nothing in it should let a reader reconstruct a current or former employer's environment.

**Always strip or redact:**

- Employer names, product names, internal team names, real coworker names
- Jira project keys, ticket IDs, internal ticket URLs
- AWS account IDs, instance IDs, VPC/subnet IDs, ARNs that include account numbers
- Internal hostnames, IPs, DNS names
- Internal Git/GitHub org and repo names
- Slack channel names, email distribution lists, internal Confluence/wiki paths
- Customer names, contract identifiers, regulator/assessor identities
- Real config that names internal services (sanitize tool/path names if they leak structure)
- Anything that could appear in a production breach disclosure: account IDs, role ARNs, OIDC subjects, key IDs

**Always sanitize but may keep:**

- Generic AWS service names, error strings, MITRE technique IDs, public IOCs already in threat-intel feeds
- Open-source project names and public CVE IDs
- Public mining pools, malware family names, public C2 infrastructure already named in vendor reports

**Process before merging a draft:**

1. `grep -iE '<employer>|<product>|<team>|<jira-prefix-1>|<jira-prefix-2>|i-[0-9a-f]|vpc-[0-9a-f]|arn:aws:[^:]+:[^:]*:[0-9]{12}'` against the new post; substitute the placeholders for your real employer, product, team, and Jira project prefixes, and review every hit
2. Re-read the post imagining a reader who works at the redacted employer; would they recognize the system?
3. For incident posts, get explicit publish approval from the relevant ticket owner before merging; preserve that approval somewhere durable
4. If the post relies on a real number (host count, alert volume, dollar figure), confirm it is publicly disclosed already or round it to an order of magnitude

When in doubt, redact. Republishing a sanitized version later is cheap; un-publishing a leak is not.

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
