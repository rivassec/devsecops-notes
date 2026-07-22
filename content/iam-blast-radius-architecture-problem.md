Title: IAM Blast Radius Is an Architecture Problem, Not a Policy Problem
Date: 2026-07-21
Modified: 2026-07-21
Author: RivasSec
Category: DevSecOps
Tags: aws, iam, devsecops, cloud-security, threat-modeling
Slug: iam-blast-radius-architecture-problem
Summary: Most IAM reviews start too late. By the time someone is staring at a JSON policy the account structure, trust boundaries, and CI paths are already decided. Least privilege is not fewer actions; it is smaller failure domains.
Cover: images/covers/iam-blast-radius-architecture-problem.png

[TOC]

## Most IAM reviews start too late

Most IAM reviews start too late.

By the time someone is staring at a JSON policy, many of the important security decisions have already been made. The account structure exists. The trust relationships exist. The CI/CD path exists. The Terraform state exists. The production data, deployment roles, and trust boundaries are already in place.

At that point, the policy review is often just cleanup. Useful cleanup, but still cleanup.

The real IAM question is not only, "Does this policy look least privileged?" The real question is, "What happens when this identity is compromised?"

---

## Policies as documents vs identities as architecture

A lot of IAM programs stay shallow because they focus on permissions as isolated documents instead of treating identities as part of the system architecture. A policy can avoid wildcards and still create an unacceptable failure domain. A role can look narrow in isolation and still become dangerous because of who can assume it, what it can mutate, or what other paths it unlocks.

Least privilege is not just fewer actions. Least privilege is smaller failure domains.

- A CI role that can deploy to every environment is not just a deployment role. It is a production-wide failure domain.
- A Terraform role that can modify IAM, networking, logging, and state stores is not just infrastructure automation. It is a control plane for the company.
- A workload identity that can read secrets, write artifacts, or assume a runner role is not just an application permission. It may be a persistence path.
- A Kubernetes service account that can patch workloads, mount secrets, or read nodes is not just a cluster detail. It can become a lateral movement primitive.

This is why reviewing IAM as JSON hygiene misses the point.

---

## Better questions than "does this policy contain `*`?"

The dangerous question is rarely, "Does this policy contain `Action: *`?"

The better questions are:

- What trust boundary does this identity cross?
- What data class can it reach?
- Can it mutate code, infrastructure, identity, or logs?
- Can it change the deployment path?
- Can it create persistence?
- Can it assume, pass, bind, or influence another identity?
- What detects misuse?
- What is the rollback path?
- What happens if this identity is compromised at 2:00 AM, and who can contain it?

Those questions move IAM reviews out of the policy document and back into the architecture.

---

## Attackers experience the environment as a graph

Attackers do not experience your environment as a set of clean policy JSONs. They experience it as a graph. Trust relationships, deployment pipelines, secrets, buckets, queues, roles, runners, clusters, and logs all become edges in that graph.

A permission that looks harmless in one context can become serious in another:

- Read access to an artifact bucket may expose deployable code.
- Write access to that same bucket may become code execution.
- Permission to update a build pipeline may become production access.
- Permission to read Terraform state may expose secrets, role names, network topology, or privileged paths.
- Permission to `iam:PassRole` may matter more than the actions listed in the role's own policy.

IAM design has to account for that graph.

---

## Where compliance checklists fall short

Compliance checklists can tell you whether a policy contains obvious broad permissions. They can tell you whether MFA is required. They can tell you whether a role was unused for 90 days.

Those checks are useful. They are not enough.

They do not always tell you whether a compromised CI runner can mutate production. They do not tell you whether a developer role can indirectly mutate identity through Terraform. They do not tell you whether an application can turn a read permission into credential exposure. They do not tell you whether logs would show the difference between normal automation and abuse.

The checklist verifies the shape of the policy. It does not verify the shape of the blast radius.

---

## Good IAM architecture starts with containment

Containment is a design choice made before the policy review begins:

- **Separate deployment identities by app and environment.** An incident in staging or an isolated service should not be able to cascade across boundaries.
- **Keep identity mutation behind tighter controls.** Restrict rights to modify roles, policies, and trust relationships far more aggressively than ordinary infrastructure changes.
- **Protect Terraform state like sensitive production data.** Treat state files as high-risk assets containing secrets, architecture maps, and privileged paths.
- **Treat CI/CD as privileged infrastructure.** Build pipelines are not generic automation; they are execution engines with direct access to production state.
- **Make role assumption paths explicit.** Require clear, auditable trust policies rather than broad, ambient role-chaining.
- **Detect sensitive actions, not just policy drift.** Monitor for abnormal role assumptions, key generation, and identity mutation in real time.
- **Make rollback work without the compromised identity.** Break-glass and incident containment paths must not depend on the very principals being isolated.

This is slower than rubber-stamping a policy PR. It is also the work that actually matters.

The safer default is easier to enforce when it is baked into the tooling. A small library like [iam-safe-defaults]({filename}iam-safe-defaults-fail-loud.md) can move the argument from "should this role have a permissions boundary" to "why is this role opting out of one," which is where you want the conversation to live.

---

## Trust made visible

IAM is not only an access control system. It is one of the main ways cloud architecture expresses trust. Every role, policy, permission boundary, service account, and deployment credential says something about what the system believes can safely happen.

When those beliefs are wrong, the incident does not stay inside the JSON file. It leaks through the architecture.

That is why mature IAM reviews should feel less like linting and more like threat modeling. The reviewer should be asking what the identity can reach, what it can change, what is unrecoverable, what it can hide, and how far the damage can spread before someone notices.

A clean policy is good. A contained failure domain is better.

The strongest IAM programs understand that distinction. They do not stop at removing wildcards. They design systems where one compromised principal cannot rewrite production, erase the evidence, and call it automation. Adoption of that shape is a control in its own right, which is a longer story told in [Adoption Is a Security Control]({filename}paved-road-adoption-as-control.md).

The goal is not a prettier IAM policy. The goal is a system where one compromised principal cannot become a company-wide incident.

IAM blast radius is an architecture problem. The policy is only where the architecture becomes visible.
