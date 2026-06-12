Title: Every Alert Is Your Alert: When IR Tooling Trips Your Own EDR
Date: 2026-07-01
Modified: 2026-07-01
Author: RivasSec
Category: DevSecOps
Tags: incident-response, edr, mitre-attack, t1105, runbook, ai-tooling
Slug: every-alert-is-your-alert
Summary: An EDR fired a true-positive on my analyst laptop while I was investigating a real cryptominer. The traffic pattern was a textbook T1105 ingress tool transfer because that is exactly what I was doing. The runbook gap is older than the LLM coding assistant that triggered it.
Status: draft
Published_after: 2026-06-19

[TOC]

During a recent incident-response engagement, the EDR on my analyst laptop fired a true-positive against my own activity. The detection was a high-severity ingress-tool-transfer alert, MITRE T1105, against a process tree that started at my shell, descended through an LLM-driven coding assistant session running with elevated permissions, and ended at two `curl` calls fetching the attacker's dropper into `/tmp` for hash and content analysis.

The detection was correct. The traffic was, by every shape the sensor examines, an ingress tool transfer.

It was also me, deliberately, doing my job.

This post is not about defending myself to a SOC. The SOC was right and the EDR was right. This post is about the gap the detection exposes: most IR runbooks still assume the suspicious transfer came from the adversary or the user. Authorized analyst tooling that mirrors adversary behavior is a third category, and almost nobody's runbook handles it.

## The setup

The parent investigation was a confirmed cryptominer running in a containerized workload. The cloud detector's correlation finding gave me the binary path, and I had it pulled out of the image's overlay2 layer within an hour. I covered the host-side investigation in a separate post: [How I Learned to Investigate Docker Image Layers During Incident Response]({filename}cryptominer-in-the-docker-layer.md). Read that first if you want the technical narrative; this post is the meta-incident that ran in parallel.

While the host investigation was active, I needed two things off the attacker's infrastructure:

1. The dropper script the binary was pulling from a content-delivery URL.
2. A second-stage payload referenced in the dropper, hosted on a public paste service.

I had two reasonable options. I could open both URLs in a browser on a sandbox VM, or I could `curl` them into `/tmp` from my laptop for hashing and side-by-side comparison with the on-disk artifacts I had already extracted.

I chose the second. Faster. No VM context switch. The files were data, not executables; I had no intent to run them. The point was a hash comparison and a static read.

The agent session I was running already had shell permissions for the investigation. I told it to fetch both URLs into a per-incident evidence directory and SHA-256 them. It did. The EDR noticed.

## What the EDR saw

From the sensor's perspective the picture was unambiguous:

- A user-space shell was running with elevated privileges
- A child process was issuing outbound HTTPS to a content-delivery domain that had not been seen on this host before
- The remote endpoints' content-types were not browsable HTML; they were script and text payloads
- The destination paths were under `/tmp/`, written for later read or execute
- The User-Agent was `curl/x.y.z`, not a browser

That is, line for line, the ATT&CK definition of T1105: `Adversaries may transfer tools or other files from an external system into a compromised environment.` The sensor doesn't get to know whether "the compromised environment" is "my laptop during a real IR engagement, used by the analyst conducting the IR." It gets the syscalls, and the syscalls were textbook.

The EDR fired. A ticket auto-generated in the issue tracker. Within the hour the detection-and-response team had escalated and closed it `true_positive`.

That last word is the interesting one. By the platform's taxonomy, the disposition was correct. The sensor was not wrong. The behavior was real. The label, however, doesn't capture the structural fact: the source was an authorized analyst, the activity was sanctioned, and the resulting telemetry needs a different kind of close than a real intrusion.

## The category most runbooks miss

When I look at IR runbooks, including the ones I have written, the dispositions tend to fall into three buckets:

- **False positive.** The detection fired, but the underlying behavior is benign. Tune the detection.
- **True positive, malicious.** The detection fired, the behavior is real, and an adversary is responsible. Run the IR playbook.
- **True positive, user-attributed.** The detection fired, the behavior is real, and a non-adversary user did it (a developer testing something, an admin running an unfamiliar tool). Document and close.

What was missing for me on this incident is a fourth bucket:

- **True positive, analyst-attributed.** The detection fired, the behavior is real, and an analyst (me, in this case) did it as part of an authorized investigation that explicitly involved adversary infrastructure.

The fourth bucket is not the third with a different word. Analyst-attributed events have specific properties that user-attributed events don't:

- The activity is **expected to look malicious** because the analyst is, by definition, interacting with adversary infrastructure
- The activity is **logged with a specific ticket** that should be the disposition's parent
- The audit trail should preserve **the link between the parent IR ticket and the EDR alert** so the same incident can be reconstructed end-to-end later
- Closure should not require the SOC to investigate the analyst's activity from scratch; the closure note should reference the parent

I have never seen a runbook with that bucket spelled out.

## Why this matters more in 2026

This incident would have happened in 2018 too. An analyst who decided to `curl` an attacker URL from a managed laptop has always been a possible source of true-positive EDR traffic. What changed is the volume.

In 2018, the analyst who reached for `curl` knew they were about to make their own laptop look briefly like a compromise. They paused. They opened a sandbox VM. They didn't, often.

In 2026, the analyst with an LLM coding-assistant session running has shell access already extended out via the assistant's permissive flag, and the easiest path from "I need to read that payload" to "the payload is on disk and hashed" is to type the request into the agent. The agent doesn't know that pulling the dropper looks identical to the malware pulling the dropper. The agent hasn't read the EDR's MITRE coverage matrix. It just executes.

This is not a problem with the agent. The agent is doing exactly what an analyst would do without one. The agent makes the friction lower, which means the same path gets taken more often, which means the same EDR alerts get fired more often, by more analysts, on more endpoints.

If your team has any LLM-driven shell access on managed laptops, your EDR is about to start logging a class of true positives that your runbook does not handle gracefully. Mine wasn't. I had to invent the closure procedure on the spot and write it down after.

## What I changed in my own runbook

The closure I ended up writing on the auto-created ticket had three parts. I am keeping all three for the next time:

**1. Self-attribution comment.** The first comment on the auto-created ticket linked it to the parent IR ticket and named the URLs and paths. The skeleton looks like: "this detection was triggered by my own IR work on `<parent ticket>`. The agent session fetched `<URL 1>` and `<URL 2>` into `<evidence path>` for hash and content analysis. Network behavior matches T1105 as expected; source was authorized analyst activity, not a compromise of `<hostname>`."

The wording matters. "Self-attributed" is more durable than "false positive" because it acknowledges the alert was correct and locates the source. Future-me reading the ticket history can reconstruct what happened without ambiguity.

**2. Parent-link.** Create a "relates to" link from the EDR ticket back to the parent IR ticket. The parent describes what was being investigated and why; the EDR ticket describes what the sensor saw. The pair is the full picture.

**3. Match-the-platform-disposition.** The vendor side had already closed the ticket as `true_positive`. Rather than dispute that, I closed the issue-tracker mirror as Done with my self-attribution comment in place. The platform tracks the right thing for the platform; the issue-tracker closure tracks the right thing for the audit history.

## What I'd want my team's runbook to add

If I were writing this into a team-level runbook (and I am, separately), the section would look like:

> When an EDR alert fires on an analyst's authorized IR endpoint and the analyst recognizes their own activity as the source, the disposition is "self-attributed authorized analysis," not "false positive." The closure must:
>
> 1. Link the alert to the parent IR ticket
> 2. Name the specific tool, command, or agent session that originated the traffic
> 3. Acknowledge that the underlying detection logic was correct
> 4. Match the EDR platform's disposition (do not argue for a different one)
> 5. Be reviewed by a second analyst within 24 hours so we are not relying on a single analyst's word

Step five is the one I want to flag. The fourth bucket has a real abuse vector: an attacker who compromises an analyst account can post a fake self-attribution comment on a real intrusion ticket and walk away. Two-analyst review is the cheapest control I can think of that closes that gap without slowing the analyst down on a real investigation.

## Closing thought

Every alert that fires on your endpoint is your alert. The phrase reads like a corporate poster, and the SOC version of it is fine: take ownership, don't punt, don't let alerts orphan. But the underneath of it, for analysts running modern tooling, is more specific. It means: the runbook for "your EDR pinged on you because you were doing IR" is your runbook to write, because nobody at the EDR vendor wrote it for you. The sensor was right. The disposition is yours.

For the host-side detail of the parent incident, see [The Miner Was In The Image Layer, Not In Memory]({filename}cryptominer-in-the-docker-layer.md).
