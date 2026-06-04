Title: IAM Roles That Fail Loud: Small Defaults, Big Difference
Date: 2026-05-12
Modified: 2026-06-04
Author: RivasSec
Category: DevSecOps
Tags: aws, iam, pulumi, python, devsecops
Slug: iam-safe-defaults-fail-loud
Summary: A small Pulumi library that treats IAM safety as a precondition: mandatory permissions boundary, no wildcard trust, no wildcard actions, every opt-out explicit.
Cover: images/covers/iam-safe-defaults-fail-loud.png

[TOC]

There's a class of AWS bug that doesn't show up until audit season: an IAM role that nobody reviewed closely, quietly granted more than it needed, sat for three years, and shows up in a Security Hub finding with `*` in its action list. The role did exactly what it was told to do. The problem is that "do what I'm told" and "refuse to do anything dumb" aren't the same default.

I put a small Pulumi library together to move that default. It's called [iam-safe-defaults](https://github.com/rivassec/iam-safe-defaults), it's under 200 lines of Python, and the behavior it changes is narrow on purpose.

## The pattern

Every AWS IAM helper I'd seen, including the one I started from, treats safety as opt-in. You can pass a permissions boundary. You can narrow the resource list. You can avoid wildcard actions. But if you *don't* do those things, you still get a working role. The function signature makes every safety measure look like a preference.

`iam-safe-defaults` inverts that. The safety measures aren't preferences; they're preconditions. If you want to skip one, you pass an explicit flag with a name that is hard to type by accident:

```python
safe_iam.create_safe_role(
    "example-role",
    assume_role_policy,
    permissions_boundary="arn:aws:iam::123456789012:policy/YourBoundary",
)
```

That works. This doesn't:

```python
safe_iam.create_safe_role("example-role", assume_role_policy)
# ValueError: create_safe_role requires permissions_boundary.
# Pass the boundary ARN, or set allow_no_boundary=True to opt out explicitly.
```

Same for trust policies. A trust policy with `Principal: "*"` raises. Same for `generate_safe_policy` — pass it `["*"]` or `["s3:*"]` as actions and it refuses unless `allow_wildcard=True` is on the call.

The opt-outs exist because there are legitimate reasons to need wildcard scope. A logging role that reads every object in every bucket. A bootstrap role. A cross-account trust with `Principal: "*"` plus a condition key. None of those should be blocked. But none of them should happen *silently* either. Every one of those calls now has an explicit flag in the source — something a reviewer can grep for, and something a future auditor can justify.

## What the checker actually catches

The old version of `is_policy_overly_permissive` in the repo checked for `"*" in actions`. That's `"*"` as a literal list element, not `"*"` as a character. It caught `Action: "*"` and it caught `Action: ["*"]`. It missed everything that matters.

`Action: "s3:*"` didn't match. `Action: "iam:*"` didn't match. `Action: ["ec2:*", "rds:*"]` didn't match. `NotAction` inversions didn't match. And the `NotAction` ones are the real problem — a policy that says "allow anything except `iam:DeleteUser`" is one of the highest-blast-radius shapes you can write, and it sailed through.

New version walks actions with `any(a == "*" or a.endswith(":*") for a in actions)`, flags `NotAction` / `NotResource` as inversions, and returns `True` on the whole class. Still a boolean, still single-purpose. It doesn't try to be a full IAM analyzer; there are better tools for that. It just catches the ones that happen by accident.

## Why Pulumi and not Terraform

Pulumi is Python. The guards are Python. The tests are Python. You can unit-test the logic without standing up a provider — Pulumi's mock runtime makes it cheap to verify "this input raises the expected exception" in under a second. The Terraform equivalent would have been an OPA policy or a Sentinel rule, with a different language, a different test harness, and a lot more ceremony for the same amount of actual behavior change.

A library this small only matters if it ships as part of a paved road — a default that developers *land on* without trying. The program shape that makes that work, including the four-month adoption stall I caused myself, is in [Adoption Is a Security Control]({filename}paved-road-adoption-as-control.md).

## The part I didn't build

This library doesn't generate permissions boundary policies. It requires one and takes an ARN. Choosing what goes in a boundary is a per-org decision — your dev accounts need different denies than your prod accounts, your data accounts need different allows than your application accounts. I thought about shipping defaults and backed off. A boundary that says `deny iam:PutRolePermissionsBoundary` is almost universal. A boundary that says "deny `ec2:RunInstances` in regions other than us-west-2" is wrong for half the audience. Making callers supply the ARN is the honest scope.

It also doesn't inject `Condition` blocks. Adding `aws:SourceAccount` or `aws:PrincipalOrgID` on every trust policy would catch a real class of cross-account confused-deputy attacks, but it would also break any legitimate cross-account pattern where the caller hasn't pre-registered. That's a tradeoff I want to make explicitly, one service principal at a time, not as a global default.

## Supply chain

One thing I did do all the way: the CI workflow that runs Bandit on every push is pinned by commit SHA for every third-party action, and every pip dependency is hash-verified. `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd` — not `v6`, not `v6.0.2`, the 40-char hash. Bandit 1.9.4 and its six transitive dependencies install via `pip install --require-hashes` against a generated lockfile with sha256 pins for every wheel. The runner explicitly nukes any private pip registry config so everything resolves against PyPI.

It felt performative to pin the tooling this hard until I remembered this is a security library. A library that lectures other people about IAM footguns and then pulls dependencies by loose version name is a joke. The bar for "I trust this" is higher than for most repos.

## Try it

```bash
git clone git@github.com:rivassec/iam-safe-defaults.git
```

Three helpers: `create_safe_role`, `generate_safe_policy`, `is_policy_overly_permissive`. Each with a single opt-out flag per guard, named explicitly enough that the code review catches it.

If you find a failure mode the checker misses, the next version will fix it. There's always another footgun. For the cluster-side cousin of this "secure by default" stance, see [Hardening Kubernetes Deployments]({filename}hardening-k8s.md).
