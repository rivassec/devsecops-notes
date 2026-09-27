Title: Every Alert Is Your Alert: When IR Tooling Trips Your Own EDR
Date: 2026-09-18
Modified: 2026-09-18
Author: Oliver Rivas
Category: DevSecOps
Tags: incident-response, edr, mitre-attack, runbook, ai
Slug: every-alert-is-your-alert
Series: Anatomy of a Container Incident
Og_image: images/og/every-alert-is-your-alert.png
Cover: images/covers/every-alert-is-your-alert.png
Summary: My EDR fired a true-positive T1105 ingress-tool-transfer on my own analyst laptop mid-investigation. The runbook gap is older than the tool that tripped it.

[TOC]

Mid-engagement on a live incident, the EDR on my analyst laptop fired a true-positive against my own activity. The detection was a high-severity ingress-tool-transfer alert, [MITRE T1105](https://attack.mitre.org/techniques/T1105/), against a process tree that started at my shell, descended through an LLM-driven coding assistant session running in a permissive execution mode, and ended at two `curl` calls fetching the attacker's artifacts into `/tmp` for hash and content analysis.

The detection was correct. The traffic was, by every shape the sensor examines, an ingress tool transfer.

It was also me, deliberately, doing my job.

This post is not about defending myself to a SOC. It is about the gap the detection exposes: every IR runbook I have written or worked from assumes the suspicious transfer came from the adversary or the user. Authorized analyst tooling that mirrors adversary behavior is a third category, and none of them handle it.

## The setup

The parent investigation was a confirmed cryptominer embedded in a containerized workload's image. The cloud detector's correlation finding gave me the binary path, and within an hour of reading that finding I had the binary pulled out of the image's overlay2 layer. I covered the host-side investigation in a separate post: [Finding the Cryptominer Hiding in a Docker overlay2 Layer]({filename}cryptominer-in-the-docker-layer.md). Read that first if you want the technical narrative; this post is the meta-incident that ran in parallel.

While the host investigation was active, I needed two things off the attacker's infrastructure:

1. The dropper script the binary referenced, hosted at a content-delivery URL.
2. A second-stage payload the binary also referenced, hosted on a public paste service.

I had two reasonable options. I could open both URLs in a browser on a sandbox VM, or I could `curl` them into `/tmp` from my laptop for hashing and side-by-side comparison with the on-disk artifacts I had already extracted.

I chose the second. Faster. No VM context switch. I was treating the files strictly as data - no execute bit, no interpreter invocation, no intent to run them. The point was a hash comparison and a static read.

That choice deserves a rule rather than a vibe, and I did not have one written down. The version I would write now: direct fetch to a managed endpoint is defensible when the goal is hash-and-static-read and you accept that fetching from corporate egress can tip your hand to an adversary watching download telemetry. Execution, unfamiliar formats, or an engagement where OPSEC matters means isolation and anonymized egress, full stop. The rule also assumes your org permits handling malware-as-data on managed endpoints and that nothing on the box auto-parses or auto-quarantines `/tmp` content; where either fails, the isolation path stops being optional. And the artifacts have a lifecycle: once hashed and read, evidence moves out of `/tmp` into the case store with tightened permissions and comes off the endpoint.

The agent session I was running already had shell permissions for the investigation. I told it to fetch both URLs into a per-incident evidence directory under `/tmp` and SHA-256 them. It did. The EDR noticed.

## What the EDR saw

From the sensor's perspective the picture was unambiguous:

- A process tree rooted at an interactive user shell, not a service
- A child process issuing outbound HTTPS to a content-delivery domain that had not been seen on this host before
- That child was `curl` with the URLs on its command line - no browser involved, and a `curl/x.y.z` User-Agent, both inferable from process telemetry without touching the TLS payload
- Script and text payloads written under `/tmp/`, the classic staging location, visible to the sensor once on disk

That is squarely the ATT&CK definition of T1105: "Adversaries may transfer tools or other files from an external system into a compromised environment." Nothing on this host told the sensor otherwise, and nothing should have: no one had pre-registered my laptop as an authorized-analysis endpoint. And I would not want it pre-registered into silence - suppression scoped to analyst endpoints is a standing blind spot on exactly the machines an attacker most wants, while fire-and-close keeps the sensor honest and the audit trail complete. The sensor got the syscalls, and the syscalls were textbook.

The EDR fired. A ticket auto-generated in the issue tracker. I recognized the alert as mine and put the self-attribution comment on the ticket (the skeleton is in the runbook section below). Within the hour the SOC had escalated and closed it `true_positive`, with no containment fired and no call to me. That sequencing was luck, not process: nothing guaranteed my comment would land before a containment decision. Pre-declaration (runbook item 6, below) closes that race only for planned fetches; for reactive ones, the cheapest mitigation is a ping to the SOC channel at fetch time - fifteen seconds that turns luck back into process.

`true_positive` is the interesting label. By the platform's taxonomy it was correct. The label, however, doesn't capture the structural fact: the source was an authorized analyst, the activity was sanctioned, and the resulting telemetry needs a different kind of close than a real intrusion.

## The category most runbooks miss

When I look at IR runbooks, including the ones I have written, the dispositions tend to fall into three buckets:

- **False positive.** The detection fired, but the underlying behavior is benign. Tune the detection.
- **True positive, malicious.** The detection fired, the behavior is real, and an adversary is responsible. Run the IR playbook.
- **True positive, user-attributed.** The detection fired, the behavior is real, and a non-adversary user did it (a developer testing something, an admin running an unfamiliar tool). Document and close.

What was missing for me on this incident is a fourth bucket:

- **True positive, analyst-attributed.** The detection fired, the behavior is real, and an analyst (me, in this case) did it as part of an authorized investigation that explicitly involved adversary infrastructure.

The fourth bucket is not the third with a different word. Analyst-attributed events have specific properties that user-attributed events don't:

- The activity is **expected to look malicious** because the analyst is, by definition, interacting with adversary infrastructure
- The activity is **traceable to a parent IR ticket**: the ticket is the disposition's parent, the EDR alert links back to it, and the closure note references it - so the SOC never investigates the analyst from scratch, and the incident can be reconstructed end-to-end later

I have never seen a runbook with that bucket spelled out.

## Why this matters more in 2026

This incident would have happened in 2018 too. An analyst who decided to `curl` an attacker URL from a managed laptop has always been a possible source of true-positive EDR traffic. What I expect to change is the volume.

In 2018, reaching for `curl` on a managed laptop meant knowingly making it look briefly compromised. The friction was the sandbox VM. Sometimes the analyst paid it; often they didn't.

In 2026, an analyst whose assistant session runs in a permissive execution mode has shell access already extended out, and the easiest path from "I need to read that payload" to "the payload is on disk and hashed" is to type the request into the agent. The agent I was running didn't know that pulling the dropper looks identical to the malware pulling the dropper. It hadn't read the EDR's MITRE coverage matrix. It just executed.

Most of this is not a problem with the agent. On the fetch itself, the agent did what I would have done by hand. The agent makes the friction lower, which means the same path gets taken more often, which means the same EDR alerts get fired more often, by more analysts, on more endpoints. One axis does break the equivalence, and it deserves its own sentence: an agent that fetches adversary content should not also read that content into its own context while it holds shell permissions. An analyst reading a script in a pager has no instruction-following channel to hijack; a shell-privileged agent parsing attacker-authored text does - the same evasion class I wrote about in [Prompt Injection Will Become a Supply Chain Evasion Technique]({filename}prompt-injection-supply-chain-evasion.md). Hash with non-LLM tooling, or read the payload in a session that has no execution rights.

If your team has any LLM-driven shell access on managed laptops, expect your EDR to start logging a class of true positives that your runbook does not handle gracefully. Mine wasn't. I had to invent the closure procedure on the spot and write it down after.

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
> 4. Match the EDR platform's disposition taxonomy; where the platform offers an expected-activity label, use it, and do not argue for a different verdict
> 5. Be reviewed by a second analyst within 24 hours so we are not relying on a single analyst's word. The reviewer verifies rather than reads: process telemetry confirms the named session originated the traffic, and the fetched URLs sit inside the parent ticket's scope. A solo shop substitutes a manager or on-call reviewer, or attaches the telemetry snapshot at close time so the verification can happen later
> 6. Where the fetch is planned rather than reactive, declare the intent on the parent IR ticket before running it; a declaration that predates the alert is the fastest triage the SOC will ever do

Step five is the one I want to flag. The fourth bucket has a real abuse vector: an attacker who compromises an analyst account can post a fake self-attribution comment on a real intrusion ticket and walk away. Two-analyst review is the cheapest control I can think of that narrows that gap without slowing the analyst down on a real investigation. Scope it honestly, though: the review defends against a compromised account. A compromised analyst endpoint is a different animal - there the attacker's traffic genuinely originates from the analyst's machine, so matching telemetry will corroborate a fake comment - and that is a full host-compromise IR, not a closure-procedure problem.

## Closing thought

Every alert that fires on your endpoint is your alert. The phrase reads like a corporate poster, and the SOC version of it is fine: take ownership, don't punt, don't let alerts orphan. But the underneath of it, for analysts running modern tooling, is more specific. It means: the runbook for "your EDR pinged on you because you were doing IR" is your runbook to write. Some platforms now ship disposition labels that get close - [Microsoft Defender XDR](https://learn.microsoft.com/en-us/defender-xdr/investigate-alerts) classifies expected security-test and red-team activity as "Informational, expected activity", and Microsoft Sentinel ships a "Benign Positive - suspicious but expected" closure - but a label is not a closure procedure. The parent-link, the attribution wording, and the second-analyst check are still yours to define. The sensor was right. The disposition is yours.

For the host-side detail of the parent incident, see [Finding the Cryptominer Hiding in a Docker overlay2 Layer]({filename}cryptominer-in-the-docker-layer.md).
