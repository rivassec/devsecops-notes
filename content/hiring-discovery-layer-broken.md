Title: The Discovery Layer Is Broken: Hiring as an Observability Problem
Date: 2026-07-11
Modified: 2026-07-11
Author: RivasSec
Category: DevSecOps
Tags: careers, devsecops, hiring
Slug: hiring-discovery-layer-broken
Summary: The senior engineering market does not have a talent shortage. It has a routing failure. Resumes compress judgment into keywords, funnels index for keywords, and the signal that senior roles actually depend on is discarded before anyone qualified sees it.
Cover: images/covers/hiring-discovery-layer-broken.png

[TOC]

## The gap between capability and first screen

The market is full of senior engineers who can debug a production outage, harden an IAM boundary, review a Terraform plan, and explain blast radius before the pager goes off.

Many of those same engineers struggle to get past the first screen.

That gap says something important about the hiring system. Hiring has a discovery problem. The industry has signal. The signal is poorly indexed, poorly routed, and poorly evaluated.

---

## Observability everywhere except the hiring funnel

Modern engineering organizations spend enormous effort building observability into production systems. They trace requests, measure latency, monitor failure modes, and build dashboards so they can understand what is happening under pressure.

Then many of those same organizations rely on one of the least observable processes in the company when hiring senior engineers.

A resume is a lossy compression format for engineering judgment. It takes years of tradeoffs, incidents, architecture decisions, migrations, security reviews, compliance work, and production scars, then compresses them into titles, company names, tools, and bullet points.

That format can find familiar labels. It struggles to find judgment.

---

## Senior signal lives in context

Senior engineering skill usually shows up in context:

- What tradeoff did you make?
- What constraint mattered?
- What failed first?
- What did you automate?
- What did you refuse to ship?
- What risk did you reduce?
- What did the system look like six months later?

Most hiring funnels do not ingest that shape of evidence. They ingest keywords.

This creates a predictable failure mode. Candidates optimize resumes for search. Recruiters scan for matches. Hiring managers complain about weak pipelines. Strong candidates disappear before anyone with enough technical context sees them.

The system then calls the result a talent shortage.

---

## Some shortages are real. This one is mostly routing.

Some shortages are real. Security, infrastructure, identity, Kubernetes, cloud architecture, incident response, and compliance automation all require people who have made real decisions under constraint. Those people are hard to find.

The deeper problem is that current hiring systems are also bad at recognizing them when they appear.

The cost is not just candidate frustration. It is organizational velocity. Teams spend months searching for the perfect resume while security debt, platform fragility, and operational risk keep accumulating.

A staff or principal engineer may have the exact experience a team needs, but describe it in production language instead of job-post language. They may write about reducing IAM blast radius instead of listing every AWS service in the account. They may talk about evidence quality, auditability, and rollback paths instead of using the phrase "DevSecOps transformation." They may have done the work without wrapping it in the vocabulary the filter expects.

That should concern every engineering leader.

If your hiring process cannot distinguish operational judgment from keyword optimization, you are selecting for resume compatibility ahead of production judgment. That is a risky thing to optimize for in senior roles.

A process that screens mostly for tool names will undervalue people who understand failure modes. A funnel that treats context as noise will discard the signal senior roles depend on.

---

## The fix starts with calibration

Hiring managers need to give recruiters sharper signal than a list of tools. A good intake should include examples of real problems the person will solve, failure modes the team cares about, and evidence that would prove competence.

For example:

- Can this person design least-privilege IAM without breaking delivery?
- Can they explain the blast radius of a bad change?
- Can they turn audit requirements into repeatable evidence?
- Can they debug a CI/CD security failure without cargo-culting controls?
- Can they make an infrastructure environment safer without creating developer friction or security theater?

Those questions produce better screens than a wall of product names.

---

## Better artifacts than resumes

Candidates also need better artifacts.

Senior engineers should document their career experience the same way incident responders document an outage: capture the problem, the constraints, the decision, the outcome, and what changed afterward. Those narratives communicate judgment far better than another bullet point listing AWS services.

We already produce better artifacts than resumes. Design reviews, postmortems, threat models, incident writeups, technical writeups, open source contributions, and conference talks all capture engineering judgment with far higher fidelity.

Most hiring systems ignore them because they are not structured for automated parsing. That is the core indexing failure.

The shape works both ways. My own writeup of a program that produced measurable outcomes plus the political stall I caused myself, [Adoption Is a Security Control]({filename}paved-road-adoption-as-control.md), is the kind of artifact I would rather be evaluated on than a bullet list. The failure-mode writeup in [The Teensy That Failed in Public]({filename}teensy-efi-bruteforce-hours-late.md) does more to communicate how I think about hardware trust than any keyword-match ever will. The complement to this post is [The Trust Decay]({filename}trust-decay-adversarial-hiring.md), which frames the same pipeline from the candidate side.

---

## What hiring teams should actually ask for

Teams should look for direct proof.

- Ask for incident stories.
- Ask for design tradeoffs.
- Ask what changed after a security review.
- Ask what the candidate automated.
- Ask where they accepted risk, and why.
- Ask how they knew a control was working in production.

These questions surface judgment. Keyword filters surface vocabulary. The two are not the same signal.

---

## The routing failure has a name

The hiring market feels broken because discovery is broken. The people exist. The work exists. The evidence exists. The pipeline loses too much signal before it reaches the people qualified to evaluate it.

Until hiring systems learn to index engineering judgment, they will keep mistaking a routing failure for a talent shortage.
