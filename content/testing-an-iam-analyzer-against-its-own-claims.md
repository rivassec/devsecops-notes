Title: Testing an IAM Analyzer Against Its Own Claims
Date: 2026-08-24
Author: Oliver Rivas
Category: DevSecOps
Tags: aws, iam, security-tooling, testing, devsecops
Slug: testing-an-iam-analyzer-against-its-own-claims
Og_image: images/og/testing-an-iam-analyzer-against-its-own-claims.png
Summary: I built a client-side IAM blast-radius analyzer, then validated it against 100 adversarial cases I did not write. The useful results were two places a green build hid a wrong answer, and the same principle fixed both.
Cover: images/covers/testing-an-iam-analyzer-against-its-own-claims.png

[TOC]

I built a client-side IAM blast-radius analyzer. You paste an AWS IAM policy and it shows the potential blast radius - escalation paths, role-assumption reach, data exposure - entirely in the browser. The page is served with a Content-Security-Policy that blocks all outbound connections and loads no third-party scripts, so the policy never leaves the tab.

Building it was the easy half. The half that decides whether anyone should trust it was validation, and the useful results were not the attacks it caught. They were the two places the tool was confidently wrong while every test stayed green.

## A green build that was still wrong

One policy could `iam:PassRole` a role in a different account and also run `ec2:RunInstances`. The analyzer reported a critical PassRole-to-EC2 execution path.

That looks right, and it is wrong. AWS only lets you pass a role to a service in the same account as the role, so a cross-account-only PassRole target cannot support that EC2 path. The finding erred toward over-warning, which is the safe direction for a blast-radius tool, but a critical finding that cannot happen is still a false positive, and false positives are how a security tool loses its audience.

The unit suite passed. The browser suite passed. Nothing was broken. The tool was just asserting something the AWS authorization model does not support. CI proves the code does what you told it to; it says nothing about whether what you told it was correct. That gap is the whole job in security tooling.

The fix gave the engine an explicit subject-account and partition, so PassRole viability became account-aware. A cross-account-only target reports as ineffective, and when the subject account is unknown the tool marks viability UNKNOWN rather than critical, because the caller could be in the pinned account and silently dropping the path would hide a real risk. The adversarial suite that caught this now passes clean, with no known false positive.

## When the review step passes without running

The second failure has nothing to do with IAM, and it is the one I think about more.

I build these tools with an automated review loop. Replaceable engineer agents make a change, then a panel of critic agents reviews it - correctness, security, reliability, and an adversarial critic whose only job is to break the result. A change ships only when every critic passes.

During one build, an upstream API had a rough few minutes and returned overload errors. Every critic in one story's panel failed to run. The orchestration logic gathered their results, saw an empty list of blocking findings, and accepted the story. It shipped with zero actual review.

The reviewers did not approve that change. They never ran. The code had converted "no findings returned" into "no findings exist" - an absent result read as approval. That is a fail-open bug in the control itself, and it is worse than the false positive. A false positive is a wrong answer you can see. A review step that passes without running hides the absence of review behind a green check.

The fix was to model the outcome, not to retry harder. A review result is now one of five explicit states: PASS, BLOCKER, ERROR, TIMEOUT, INVALID_RESPONSE. Promotion requires that every required critic returned PASS. A missing critic, a null result, a timeout, an error, or a malformed response is a blocker: it stops promotion, writes a durable record of what failed, retries within a bounded policy, and requires a real review before anything ships. Fifteen fault-injection cases now assert that no combination of missing or broken critic results can ever reach "approved".

## The control caught a bug in its own construction

The run that built that fail-closed control - implement the model, then review it - finished with the story held, not approved. The review loop that would eventually gate every change already existed, and it turned on the change under construction: the adversarial critic found two real problems in the code meant to make review trustworthy. A debug scratch file had leaked into the deploy tree and would have shipped to production, and a residual fail-open let a malformed critic id slip an acceptance through. The adversarial critic plus a decision model that treats "held" as a real state refused to rubber-stamp the very control built to stop rubber-stamping.

A green pipeline would have merged it.

## The evidence that mattered

The scale numbers are fine - 1,397 passing tests, three browsers, 100 adversarial cases across three independent suites, seven AWS policy families each analyzed or explicitly failed closed. But the signals worth trusting are the ones about failure behavior:

- Parser hardening that fails closed on duplicate JSON keys, which can hide a dangerous permission behind a benign one, and on Unicode homoglyph action names.
- Rendering and export that treat every policy-controlled string as untrusted text, with no injection in the UI or in Markdown export.
- A 52 MB, 10,000-statement policy rejected in about 9 ms, before any graph work.
- Live verification after every deploy, not just a green pipeline.
- The two failures above written into the release notes, not buried.

## The principle underneath both

Unknown, unavailable, malformed, timed-out, and failed are explicit states. An empty array, a missing result, a rejected promise - none of them mean safe or approved. They mean the system does not know, and a system that cannot establish a trustworthy result should fail closed and say so.

That one rule runs through the whole tool. It returns a machine-readable "unsupported" code on policy families it does not fully model instead of guessing as though the input were an identity policy, because unsupported is not the same as safe. It refuses to expand a `Deny` with `NotPrincipal` into an ordinary "deny everyone except X" exclusion: NotPrincipal in a Deny is matched by exact ARN, so a naive reading can deny far more or far fewer principals than intended, and principals with permissions boundaries add a further wrinkle. It treats an SCP or RCP as a ceiling, never a grant. And the review workflow refuses to accept a change a critic never actually reviewed.

A security tool earns trust through how it behaves when it cannot be sure. The green build is table stakes. What the tool does when the honest answer is "I do not know" is the part worth reading.
