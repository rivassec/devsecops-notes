# Vendored web build - do not edit here

The files under `content/tools/iam-blast-radius/` (the IAM Blast Radius web tool:
`index.html`, `app.js`, `worker.js`, `styles.css`, `samples.js`, and
`engine/`) are a VENDORED copy of the shipped web build from the tool's own repo:

- Source: https://github.com/rivassec/secure-iam-lint
- Pinned commit: 4cadd9d5942ca726626666bc2626ce5140f9e579
- Served at: https://rivassec.com/tools/iam-blast-radius/

The blog only SERVES these files; the source of truth (engine, tests, CLI, GitHub
Action) lives in secure-iam-lint. Do not edit them here - change them upstream and
re-sync with `scripts/vendor-iam-blast-radius.sh`.
