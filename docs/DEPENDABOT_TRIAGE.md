# Dependabot alert triage: pending investigation

**Status**: BLOCKED on GitHub token scope refresh

## What I found

- GitHub push output showed: `remote: GitHub found 1 vulnerability on rivassec/devsecops-notes's default branch (1 low)`
- Alert URL: <https://github.com/rivassec/devsecops-notes/security/dependabot/1>
- Dependabot config at `.github/dependabot.yml` correctly configured for pip + github-actions weekly updates
- Zero open Dependabot PRs currently, which means the alert is either auto-dismissed, awaiting manual review, or in a package without a fix release yet

## What I could not do without scope refresh

The `dependabot/alerts` API endpoint requires the `security_events` scope,
which the current `gh auth` token does not have. Refreshing the scope
requires an interactive prompt.

## How to resolve

**One-time scope refresh** (open browser flow, 30 seconds):

```bash
gh auth refresh -h github.com -s security_events
```

**Then fetch the alert details**:

```bash
gh api repos/rivassec/devsecops-notes/dependabot/alerts \
  --jq '.[] | {state, severity: .security_advisory.severity, package: .security_advisory.vulnerabilities[0].package.name, summary: .security_advisory.summary, first_patched: .security_advisory.vulnerabilities[0].first_patched_version.identifier, fix_available: (.security_advisory.vulnerabilities[0].first_patched_version != null)}'
```

Or just visit <https://github.com/rivassec/devsecops-notes/security/dependabot/1>
in your browser.

## Suggested fix path

Once you can see the alert:

- If it's a pinned pip dep in `requirements.in`: bump the version in
  `requirements.in`, then regenerate `requirements.txt`:
  ```bash
  pip-compile --generate-hashes --resolver=backtracking requirements.in
  ```
- If it's in a transitive dep with no fix: dismiss with reason via GitHub UI
- If it's in a GitHub Actions dep: the weekly Dependabot job will PR it
  soon; no action needed unless you want to force it

Delete this file after triaging.
