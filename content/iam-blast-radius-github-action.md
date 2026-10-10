Title: IAM Blast Radius in CI: Designing a Gate That Fails Closed
Date: 2026-10-09
Modified: 2026-10-09
Author: Oliver Rivas
Category: DevSecOps
Tags: aws, iam, github-actions, ci-cd, devsecops, cloud-security
Slug: iam-blast-radius-github-action
Summary: A security gate has to say "I don't know" and block on it. The design decisions behind the IAM Blast Radius GitHub Action, and how to run it as a control.

[TOC]

## Scanners optimize for signal. Controls must optimize for not lying.

Most IAM risk does not arrive as one obviously dangerous policy. It accumulates: the wildcard added "temporarily", the `iam:PassRole` without an `iam:PassedToService` restriction, the trust policy that quietly gains another account. Each change looks reasonable on its own. Combined with the permissions and trust relationships already in place, it can substantially expand what a compromised identity could reach.

The problem is not that engineers cannot read JSON. It is that reviewing individual permissions is not the same as reasoning about their consequences.

The [IAM Blast Radius analyzer](/tools/iam-blast-radius/) does that reasoning in a browser tab, without sending the policy anywhere. That helps when someone already suspects a policy. It does nothing for the change nobody looked at twice. So the same engine now ships as a GitHub Action on the [GitHub Marketplace](https://github.com/marketplace/actions/iam-blast-radius), and the analysis moves into the pull request.

Putting a scanner in CI does not make it a security control. A control needs a defined enforcement boundary, predictable failure behavior, and an explicit way to represent uncertainty. If the engine cannot analyze a policy, it must not report success. If a policy is never scanned, that gap must not be mistaken for a clean result.

So this post is organized around three questions:

1. What does the engine know?
2. What happens when it does not know?
3. Can someone get past the gate without defeating the engine?

Then, how I would roll it out.

## What the engine knows

It reports potential blast radius, not effective permissions. It reasons about the policy in front of it, not your whole organization, so it cannot see the SCPs, permissions boundaries or session policies layered on top unless you scan those too. Findings are graded by how much the policy alone supports them. That limitation is stated rather than hidden, because a control that overclaims gets ignored the first time it is wrong.

It recognizes 13 families of privilege escalation, from `iam:PassRole` into compute and policy version tricks to cross-account role assumption and data access through KMS. Version 1.1.0 added one I kept finding in real policies: taking over compute that already holds a role. `ssm:SendCommand`, `ssm:StartSession`, EC2 Instance Connect and presigned SageMaker notebook URLs give code execution on something that already has a role, and that role is now yours. No `iam:PassRole` required.

What makes this usable is restraint. Every escalation family ships with "does not fire" fixtures: the conditioned grant, the explicit deny that really blocks, the read-only variant. A false positive in a gate costs more than a missed finding in a report, because it teaches engineers to route around the gate. I wrote about building that corpus in [Testing an IAM Analyzer Against Its Own Claims](testing-an-iam-analyzer-against-its-own-claims.html), including the two times a green build was hiding a wrong answer.

## What happens when it does not know

### Unknown is a result, and it blocks

Most linters return two answers: problems found, or none found. A gate needs a third. If the engine cannot parse a file, meets a condition it does not model, or runs out of time, the honest output is "unknown", and an unknown that merges is indistinguishable from an approval.

So the Action has an explicit exit code for it:

| Exit | Meaning | Check |
| ---- | ------- | ----- |
| `0` | Analyzed; nothing at or above `fail-on` | pass |
| `1` | Analyzed; findings at or above `fail-on` | fail |
| `2` | Usage or configuration error | fail |
| `3` | Could not analyze: fail closed | fail |
| `4` | Internal error | fail |

Exit `3` covers malformed or unsupported input, incomplete coverage, and every resource ceiling: time per policy, number of files, total bytes. A multi-file run reports its worst result, so one file the engine could not read fails the run even when the rest are clean. A partial scan is never reported as a pass, and no configuration turns a `3` into a `0`.

The cost is friction. Some pull requests will fail on input the engine does not understand yet. I accept that trade deliberately: a gate that quietly passes what it cannot read is worse than no gate, because it manufactures confidence.

### Explicit context beats inference

Three inputs are designed to be inconvenient, because inference here would fail open.

- **`family` is required and never detected.** An identity policy, a role trust policy, a resource policy, a permissions boundary, a session policy, an SCP and an RCP are evaluated by different rules. Guessing wrong produces confident nonsense, so you say which one you are scanning, and a repository with several kinds runs the Action once per kind.
- **`partition` has no default.** An account ID does not tell you whether a role lives in `aws`, `aws-us-gov` or `aws-cn`. Defaulting to `aws` would make cross-partition verdicts look certain when they are assumptions. Leave it unset and any verdict that depends on it fails closed.
- **Resource policies need the resource.** Without the ARN of the resource the policy is attached to, the Action does not guess what "this bucket" means. It fails closed.

The principle is the same in all three: when the engine would have to assume something to give an answer, it asks instead, and a missing answer is a failure, not a pass.

A workflow with that context stated:

```yaml
name: IAM Blast Radius

on:
  pull_request:
  push:
    branches: [main]

permissions: {}

jobs:
  iam-scan:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: rivassec/secure-iam-lint@c39edcd7adb383df7c1f7598f0fb72e80be36562 # v1.1.0
        with:
          paths: policies/**/*.json
          family: identity
          partition: aws
          fail-on: high
```

The workflow grants nothing at the top level and `contents: read` to the one job that needs it. Both actions are pinned to commit SHAs; `rivassec/secure-iam-lint@v1` is the moving major tag if you prefer to track releases.

## Can someone get past the gate without defeating the engine?

### The scanner assumes its input is hostile

A policy gate reads content from pull requests, including pull requests from people you have never met. That makes the scanner part of your attack surface, so it is deliberately boring:

- **It reads files and runs nothing.** No Terraform, no npm, no shell, no command from the repository. Policy content stays data.
- **No runtime dependencies, no build step.** What is in the tagged commit is what executes. The npm package is published with build provenance through OIDC trusted publishing.
- **Hard ceilings.** Time, file count and total size are bounded, and hitting a bound is a fail-closed exit, not a truncated pass. A pull request cannot make the gate slow, and it cannot make it give up quietly.
- **SARIF is opt-in and separated.** The maintained pattern in [ACTION.md](https://github.com/rivassec/secure-iam-lint/blob/main/ACTION.md) keeps the scan job read-only, gives `security-events: write` only to a separate upload job, publishes the SARIF artifact even when the scan fails, skips uploads for fork pull requests, and never uses `pull_request_target` with an untrusted checkout. That is privilege separation, not a clean room: the SARIF the upload job handles was still derived from untrusted policy files, and it is treated as untrusted data too.

### The CI gate is part of the security boundary

Fail closed handles one failure mode: the scan runs and cannot reach a verdict. The other is invisible to the Action: the scan never runs against the policy that gets deployed.

Nobody needs to defeat the analysis engine to merge a risky policy. It is usually easier to route around it:

- **Coverage gaps.** The scan watches `policies/**/*.json`, but trust policies live elsewhere, or the deployed JSON is generated from templates the scan never sees.
- **Workflow edits.** A pull request lowers `fail-on`, narrows `paths`, or removes the job.
- **Unprotected merges.** The check fails correctly and the pull request merges anyway, because nothing requires it to pass.

None of these exploit the scanner. They exploit the pipeline around it. So the gate needs the same treatment as any other control: required in a branch ruleset, workflow file under CODEOWNERS review, an inventory of where every deployable policy comes from with a scan path for each, and alerting on skipped runs and configuration changes, not only on failures.

## Rolling it out as a control

Turning on a blocking check across an estate on day one is how security tooling earns a bypass. The rollout I would use:

1. **Observe findings, enforce unknowns.** Start with `fail-on: none`. Findings are reported but do not block; fail-closed exits still do, because `none` never turns a `3` into a `0`. The first week tells you two things: how much existing risk you are carrying, and where the engine needs context it does not have yet.
2. **Fix the unknowns first.** Every exit `3` is either missing context (`family`, `partition`, a resource ARN) or input the engine does not support. Resolve them before raising the threshold, or the gate's first impression will be noise.
3. **Ratchet the threshold.** Move to `fail-on: high` once the existing findings are triaged: fixed, or accepted by someone who owns the risk. Lower it later if the signal holds.
4. **Route findings to owners.** The engineer who wrote the policy should see the finding in their pull request, and the person who can accept the risk should own the exception, not the security team by default.

## Where it fits

This does not replace the architecture work. As I argued in [IAM Blast Radius Is an Architecture Problem, Not a Policy Problem](iam-blast-radius-architecture-problem.html), most of the risk is decided before anyone opens a JSON file: account boundaries, trust relationships, which pipeline can reach production. A policy gate cannot fix a flat account structure.

What it can do is hold the line on drift, in the place where drift happens. It does not promise that every passing policy is safe, and it cannot guarantee that every risky change is detected. It promises something narrower and more useful: an enforceable, auditable check that names potential permission risk during review, and refuses to approve what it could not analyze.

## Try it

- GitHub Marketplace: [IAM Blast Radius](https://github.com/marketplace/actions/iam-blast-radius)
- Source, issues and the full input reference: [rivassec/secure-iam-lint](https://github.com/rivassec/secure-iam-lint)
- No CI handy? Paste a policy into the [browser version](/tools/iam-blast-radius/). Same engine, nothing leaves your machine.

If it flags something it should not, or misses something it should catch, open an issue with a redacted policy and what you expected. Those reports become fixtures.
