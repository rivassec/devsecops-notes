Title: secure-iam-lint v1.2.0: Catching Guardrails That Never Fire
Date: 2026-10-21
Modified: 2026-10-21
Author: Oliver Rivas
Category: DevSecOps
Tags: aws, iam, scp, github-actions, ci-cd, devsecops, cloud-security
Slug: secure-iam-lint-v1-2-0
Summary: secure-iam-lint v1.2.0 flags SCP and RCP guardrails that never fire, adds baseline mode for noise-free PRs, and stabilizes SARIF fingerprints.

[TOC]

## A region fence that fences nothing

This service control policy is meant to keep an account inside two approved regions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyOutsideApprovedRegions",
    "Effect": "Deny",
    "NotAction": ["iam:*", "sts:*"],
    "Resource": "*",
    "Condition": {
      "StringNotLike": {
        "aws:RequestedRegion": ["us-east-1", "us-west-2", "*-*-?"]
      }
    }
  }]
}
```

The third value looks like a harmless pattern added for a future region. It matches every current AWS region name. `StringNotLike` is true only when the requested region matches none of the values, so whenever a request carries a region, this condition is false and the Deny never fires. The fence is decorative. Nothing in this policy keeps requests out of other regions, while it still reads like a control during code review.

The rest of the policy is the usual shape for a region fence. The `NotAction` carve-out is there for global services: IAM, for example, is served from a single endpoint in us-east-1, so without the exemption its calls would be denied whenever us-east-1 sits outside the fence. AWS's own example exempts a longer list of services; the snippet keeps two to stay short, so copy AWS's list, not this one.

Version 1.1.0 of [secure-iam-lint](https://github.com/rivassec/secure-iam-lint) called this policy CLEAN with exit `0`. Version 1.2.0 reports it as High and fails the check at the default `fail-on: high`:

```text
$ iam-br --family scp --partition aws policy.json | jq '.findings[0] | {id, severity, title, why}'
iam-br: status=complete exit=1 reason=FINDINGS_AT_OR_ABOVE_THRESHOLD findings=1 blocking=1
{
  "id": "SCP-GUARDRAIL",
  "severity": "high",
  "title": "SCP guardrail that never fires (no-op Deny)",
  "why": "This Deny is gated by a negated operator on aws:RequestedRegion whose values together match every region, so the condition is never true when the key is present. The guardrail is a no-op: it looks protective but removes nothing from the ceiling."
}
```

The first line is the status summary on stderr; the CLI writes its full result as JSON on stdout, trimmed here with `jq`. Remove the `"*-*-?"` entry and the same policy returns to CLEAN.

For readers new to the tool, secure-iam-lint is an open-source CLI and GitHub Action that reads AWS IAM policies in pull requests and reports their *potential* blast radius before they merge. That includes the privilege escalation, data exposure and cross-account reach they open up. The npm package is `secure-iam-lint`, its CLI is `iam-br`, and the Action is listed on the GitHub Marketplace as IAM Blast Radius. I introduced the analyzer, and why blast radius is an architecture problem, in [IAM Blast Radius Is an Architecture Problem]({filename}iam-blast-radius-architecture-problem.md). This post covers the changes in v1.2.0.

## Guardrails get judged too

In my experience, service control policies (SCPs) and resource control policies (RCPs) are the controls teams assume work: they sit above every member account and are rarely re-read until an incident. The failure that worries me most produces no error at all: a Deny whose condition can never be true.

v1.2.0 treats a guardrail that never fires as a High finding. It now catches:

- a negated region list (`StringNotLike` and its variants) whose values together match every region, as in the example above;
- a conditioned Deny whose `NotAction` matches every action, leaving nothing to deny (an unconditioned one already failed closed);
- an RCP organization perimeter that admits any AWS organization, or a positive org comparator that inverts the perimeter;
- conditions that are always or never true, including `Null "true"` on keys that are always present, contradictory `Bool` values and a `Resource` scope that cannot match;
- a Deny pinned to principal values no request ever carries, such as a literal `*` under `StringEquals` on `aws:PrincipalArn`.

Inverted region and org fences now report High. So do bypassable MFA gates in an SCP, such as plain `Bool aws:MultiFactorAuthPresent "false"`, which misses requests where the key is absent. In v1.1.0 some of these reported only medium and others passed as CLEAN, including that bypassable MFA gate on a region fence. A correctly written MFA gate that lists its actions (`BoolIfExists`) now reads CLEAN, where v1.1.0 failed closed on it with exit `3`; one written with `NotAction` still exits `3`. SecureTransport conditions aren't modeled yet: an inverted one in an SCP reports High, and any SecureTransport-gated Deny, correct or not, still exits `3`. In an RCP, these MFA and SecureTransport gates exit `3` without a High finding.

A guardrail Deny receives credit only for behavior the evaluator models. If it combines a modeled condition with an unknown condition key, an unknown operator or a negated set-qualified operator, the scan exits `3` instead of guessing that the Deny probably works. Guessing fails open when a Deny only appears to narrow a grant.

## Baseline mode fails only on new risk

Enabling a gate in a repository with existing policies usually produces a wall of findings on day one. A common response is `continue-on-error`, which leaves the gate unable to block anything.

v1.2.0 adds baselines. Generate one, review it, commit it, and new findings fail the check while the accepted ones don't:

```yaml
- uses: rivassec/secure-iam-lint@v1
  with:
    paths: policies/**/*.json
    family: identity
    baseline: .iam-baseline.json
```

1. **Generate it** by running once with `baseline-output: .iam-baseline.json` in the Action. Locally, run `iam-br --family <family> --format baseline --artifact-uri <repo-relative path> <file>` per file; the `--artifact-uri` matters, because baseline keys are bound to the path.
2. **Review it** before committing. Committing a baseline accepts every result it contains, Critical ones included; `baseline-output` warns on stderr when it writes a Critical entry, so read those first.
3. **Commit it** and pass it as `baseline:`.

Each acceptance is bound to the finding's identity, including file, rule, rule version, severity, actions, resources, trusted principals and condition values. Changing any of them makes the finding fire again. Widen a trust policy to a second account and the old acceptance no longer covers it. An acceptance covers that exact finding and nothing that later grows out of it.

A baseline can also accept two of the fail-closed states: an `UNKNOWN_ACTION` or an `UNSUPPORTED_CONDITION`, each bound to its exact sorted list of actions or condition keys. An accepted one no longer counts toward exit `3`; if nothing else blocks, the run exits `0`, reported as partial (`CLEAN_WITH_BASELINE`). A different unknown action still fails closed. Everything else is never accepted: usage errors, internal errors, malformed input, a blocked family and a blown time budget still fail the run. The Action also reports `baseline-stale-count`: entries for findings that were fixed or deleted and no longer match anything. Remove those entries from the file by hand. Regenerating the baseline would also accept any new findings, so if you regenerate, review the diff before committing.

The baseline is repository content, so a pull request can add an entry for its own new finding, the same way it can edit the workflow. Keep the file inside your review boundary: a CODEOWNERS entry only helps if branch protection requires code-owner review, and you should read added entries before merging. Until a human reviews it, a pull request's own check is not trustworthy, because the pull request can also change the workflow that runs it. The Action's documentation says not to pass a baseline from pull-request-controlled content if the check must hold before review, and not to use `pull_request_target` for untrusted pull requests. I haven't built a pre-review setup like that myself.

## Resource policies can now pass

Earlier versions failed closed on nearly every resource policy. That was safe and rarely useful. v1.2.0 lets a resource policy exit `0` when every part is modeled, including KMS key-owner delegation, same-account grants, service grants bound to your own account and deny-only policies. That still requires telling the scan which resource the policy is attached to (`resource-arn`, plus `resource-type` and `resource-account` where relevant); without it, the scan exits `3` as before. The verdict is only as good as that context, and the Action applies one context to every file its `paths` match, so scan each resource policy in its own step.

Anything the engine does not model still exits `3`, with the JSON path of the statement it stopped on. Examples include `NotPrincipal`, Allow with `NotAction` or `NotResource`, unknown condition operators, `CanonicalUser` or `Federated` principals and actions from another service. Reviewers get a specific statement to inspect instead of a generic failure.

## New detections

- **DB-AUTH**: `rds-db:connect` is IAM database authentication, which is credential-equivalent. High unless every resource pins a concrete `dbuser:<resource-id>/<user>` (the ARN uses the database or cluster resource ID, not its name).
- **PASSROLE-UNSCOPED**: `iam:PassRole` on `*` or any all-roles pattern now reports without a companion launch action. It combines with whatever compute permission the holder has elsewhere, and the engine cannot see that from one policy.
- **OBJECT-ACL-WRITE**: `s3:PutObjectAcl` and `s3:PutObjectVersionAcl` can make objects public or share them cross-account, unless Object Ownership is `BucketOwnerEnforced` (the default for new buckets, which rejects ACL changes); S3 Block Public Access also stops the public case. Both are bucket or account settings a policy cannot show. High on `bucket/*` or broader, medium on one named object.
- **Open federated trusts are Critical.** A GitHub OIDC trust with a missing or wildcard `sub` (`*`, `repo:*`) lets any repository's workflow assume the role. [IAM now refuses](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html#idp_oidc_Create_GitHub) to save one whose `sub` is missing or only a wildcard, so the shapes you will still meet are prefixes like `repo:*` and policies IAM hasn't seen yet, such as infrastructure code before it is applied. A Cognito trust whose `aud` is not pinned to a literal identity pool id, a wildcard for example, admits identity pools in any account through the basic (classic) authentication flow, including one an attacker creates in their own. A Cognito trust with no `aud` at all can no longer be saved, but [per AWS](https://docs.aws.amazon.com/cognito/latest/developerguide/role-trust-and-permissions.html) an older one still admits any identity pool in the role's own account, and the tool rates it Critical as well. These now fail even at `fail-on: critical` (`--threshold critical` in the CLI).
- **Admin-equivalent self-targeting grants are Critical**: attaching, putting or versioning a policy on `*` or on the caller's own identity.

`DATA-EXFIL` severity now scales with breadth. One named secret or parameter is medium, while `*`, account-wide or ambiguous resources remain high.

## Finding identities that survive edits

Every finding carries a stable identity, written into the SARIF `partialFingerprints` and used for baseline entries. In v1.1.0 that identity included the statement's position, so inserting a statement above a finding gave it a new identity even though nothing about the risk had changed.

v1.2.0 identities describe *what* the finding is: rule, actions, resources, principals and the affected condition blocks. Position is in neither of the two hashes built from that identity:

| | SARIF fingerprint | Baseline key |
|---|---|---|
| Hash | SHA-256 truncated to 128 bits (`iamBlastRadius/semanticIdentity/v2`) | full SHA-256 |
| Also binds | occurrence ordinal | file path, severity, rule version, occurrence ordinal |
| File | not hashed; comes from the SARIF result's location | hashed, so an acceptance never covers another file |

## Upgrading from v1.1.0

If you use `@v1`, your next run is already on v1.2.0 and may fail on findings that are new or now more severe. Pin the full commit SHA of v1.1.0 or v1.2.0 if you want to choose when that happens.

Then plan one pass:

1. **Triage severity changes.** Self-targeting admin-equivalent grants moved to Critical, for example, and several guardrail findings moved to High.
2. **Re-dismiss code-scanning alerts.** The fingerprint key changed, so per the Action's documentation, dismissed alerts reopen once under the new key and need dismissing again. I haven't checked this on a live repository myself.
3. **Start baselines after the upgrade.** Baselines are new in v1.2.0, so generate yours once the triage is done.

Once you use baselines, the same applies to future upgrades: severity is part of a baseline entry, so an accepted finding whose severity rises fires again.

## Nothing passes on a guess

The rule from v1.0 holds, with one deliberate exception. When the engine encounters a structure it cannot fully analyze, it exits `3`, says why (with the JSON path where it can point to one), and fails the check. No threshold or `fail-on` setting turns that result into a green check. The one exception is the baseline described above: a reviewed `UNKNOWN_ACTION` or `UNSUPPORTED_CONDITION` can be accepted, which narrows the promise from my earlier post on the CI gate that no configuration turns a `3` into a `0`.

Many of the security fixes in this release came from my adversarial review rounds that tried to make the analyzer mark a risky policy CLEAN, and the bypasses they found became regression tests. Some of those bypasses were regressions introduced and caught during v1.2.0 development, before anything shipped. One example: a Deny covering only the catalogued `ssm:GetParameter*` actions briefly suppressed the wildcard grant. Now a partial Deny narrows the finding and suppresses it only when it covers the whole grant. I described the testing approach in [Testing an IAM Analyzer Against Its Own Claims]({filename}testing-an-iam-analyzer-against-its-own-claims.md).

## Get it

- **GitHub Action:** `uses: rivassec/secure-iam-lint@v1` (the `v1` tag points at v1.2.0), or pin the full commit SHA from the [v1.2.0 release](https://github.com/rivassec/secure-iam-lint/releases/tag/v1.2.0). Listed on the [GitHub Marketplace](https://github.com/marketplace/actions/iam-blast-radius).
- **npm:** `npm i -g secure-iam-lint`, published with npm provenance.
- **Source and full changelog:** [github.com/rivassec/secure-iam-lint](https://github.com/rivassec/secure-iam-lint/blob/main/CHANGELOG.md).

What I plan next: wider action-catalog coverage and Pulumi support in v1.3.0, then more Deny shapes (`aws:ResourceTag/*`, `aws:TagKeys`, NotAction-only Denies).
