Title: Adoption Is a Security Control: Notes from Paving a Road
Date: 2026-05-21
Modified: 2026-06-04
Author: RivasSec
Category: DevSecOps
Tags: devsecops, platform-security, paved-road, pulumi, ci-cd, cloud-security
Slug: paved-road-adoption-as-control
Summary: A security control developers can route around is not a control. Field notes from rebuilding a cloud security model around making the secure path the easy path: 40% lower remediation time, 27% lower pipeline latency, and a four-month adoption stall I caused myself.
Cover: images/covers/paved-road-adoption-as-control.png

[TOC]

## Adoption is a security control

A security control developers can route around is not a control. It is a checkbox.

In a previous life, I watched our cloud security model fail in a very specific way. Developers would hit a build break, file a ticket, and ship the workload through a side door. The controls all worked on paper. The audit report read fine. Adoption was the problem, and adoption is what determines whether a control exists in practice or only in slides.

<div class="tldr"><strong>TL;DR.</strong> Make the secure path the easy path, own it inside the security org, and aggressively retire the side doors. The political work is harder than the technical work.</div>

So I rebuilt the model around a single idea: make the secure path the easy path, and make every other path expensive enough that nobody picks it twice. Eighteen months in:

<div class="metrics">
  <div class="metric"><div class="num">-40%</div><div class="label">Remediation Time</div></div>
  <div class="metric"><div class="num">-27%</div><div class="label">Pipeline Latency</div></div>
  <div class="metric"><div class="num">4 mo</div><div class="label">Adoption Stall</div></div>
</div>

The reason it worked is not novel - "paved road" as a concept has been written about for years - but the specifics of *why* it stopped failing the way it had been failing are worth writing down. Three things mattered, in this order.

## 1. Modules with the controls baked in

I shipped Pulumi modules with the controls already inside them. Encryption at rest, IAM least-privilege scaffolding, network segmentation defaults, structured logging, all wired up. A developer picked a module, got a workload, and shipped. The controls happened because the module was *inherently* built that way - they were not a checklist the developer had to remember. The smallest standalone example of that posture is [iam-safe-defaults]({filename}iam-safe-defaults-fail-loud.md), a tiny Pulumi library that refuses to mint a role without a permissions boundary unless the caller types an explicit opt-out.

The CI side mirrored this. We gated [Trivy](https://github.com/aquasecurity/trivy) and [Checkov](https://github.com/bridgecrewio/checkov) directly in the pipeline and surfaced their findings in pull request comments, not in a quarterly report. Findings showed up where the developer was already looking, before deploy, while the change was small and the context was fresh. By the time a workload reached production, the failure modes that used to dominate audit findings had been priced out at the PR level.

The principle here is unsexy: the secure default has to be the *path of least resistance*, not the path of most virtue. If the developer has to type more, remember more, or wait more for the secure path, the side door wins. The same logic applies one layer up the stack: TLS misconfigurations stop being a security problem the moment the cert lifecycle is automated by default, which is the lens I take in [TLS Has Three Jobs]({filename}tls-three-jobs.md).

## 2. The modules lived inside the security org

Owning the modules in security made the iteration loop tight. When CIS benchmarks shifted, when a new CVE surfaced, when an internal incident produced a hardening lesson - I pushed a module update, and the next deploy picked it up. Security owned both the responsibility and the means to act on it. There was no quarterly cross-team negotiation about whose backlog the fix lived in.

This is the part that is uncomfortable to write down because it sounds like an empire grab. It is not. The accountability for cloud misconfiguration *already* sat with security; what changed was that the levers to actually fix things sat in the same place. The platform team did not lose anything they wanted - they wanted to build platform features, not chase down stale IAM defaults.

The boundary I drew was that the modules were security's, the runtime platform was platform's, and the contract between them was the module API. That contract was the negotiation surface, and once we agreed on it, both teams could move independently.

## 3. Aggressive deprecation

The first rollout was a soft launch. Both the new module path and the legacy paths existed side by side, on the theory that developers would naturally drift toward the better experience.

Adoption stalled for **four months**.

What was happening in retrospect is obvious: as long as two paths existed, the new path was extra work for any team that already had a working pattern in the old one. The new path was easier for greenfield workloads, but most workloads were not greenfield, and the migration cost is what dominated.

I retired the legacy patterns hard. Stopped accepting them in CI, marked them deprecated in code review, and gave teams a fixed window to migrate. Adoption climbed within a single sprint. The lesson - one I keep relearning in different forms - is that *paths in addition* are not adopted, paths in *replacement* are. If you are not willing to break the side door, you are not actually building a paved road. You are building a recommendation.

## What I underestimated: the political cost

The technical lift was the easier half. The harder half was a quarter of feeling like I had crossed an organizational line.

Platform engineering felt boundary-crossed when modules started shipping that touched their substrate. Their concern was reasonable - we were sitting in the seam between their platform contract and the developers consuming it, and we had not asked first. I spent real time co-designing the module review rotation with them, giving platform a structural seat in what got merged and when. That review process slowed initial throughput a bit, but it eliminated an entire class of trust friction that would have surfaced later as veto power applied at scale.

If I were starting this work fresh, the single thing I would do differently is invite platform into the module review process *before* shipping the first module - not after. The technical design is mostly tractable; the org design is where the work actually lives.

## What survived contact

The version of this system that ended up in production looked different from the one I designed on paper. It survived contact with the developer experience team, the platform team, and the audit team. Each of them moved a constraint, and the final shape was the intersection of all those constraints.

That's the work. Not the architecture diagram, not the pull request that shipped the first module - the eighteen months of operating the thing inside a real org, watching it not quite fit, and reshaping it. The numbers (40%, 27%, the stalled four months) are real, but they are not the point. The point is that adoption is the security control, and everything else is plumbing that exists in service of adoption.

If developers can route around your control, the control doesn't exist. If they can't, you have done the work.
