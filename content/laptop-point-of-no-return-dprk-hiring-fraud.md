Title: The Laptop Is the Point of No Return: DPRK IT Worker Fraud
Date: 2026-10-15
Modified: 2026-10-15
Tags: insider-threat, north-korea, hiring-fraud, hiring, detection-engineering, edr
Category: Threat Intelligence
Series: Hiring as an Adversarial System
Slug: detecting-dprk-it-worker-hiring-fraud
Og_image: images/og/detecting-dprk-it-worker-hiring-fraud.png
Author: Oliver Rivas
Summary: The DPRK IT worker problem is usually told as an EDR story. By the time the alert fires, you have already lost. Move detection left of the laptop.
Cover: images/covers/detecting-dprk-it-worker-hiring-fraud.png

[TOC]

The North Korean IT worker problem is usually told as an endpoint story. Someone installs a remote-access tool, the SIEM lights up, and you pull the machine. That story is real, and I have lived it. It is also a description of a failure. By the time the alert fires, a hostile operator has held a corporate laptop, VPN credentials, and source-code access - for hours in the lucky cases, for weeks or months in the reported ones. The detection worked. The program did not.

The uncomfortable part is that the cheapest, highest-yield controls against the common operator belong to recruiting and HR rather than security, and in my experience most teams are not running them. They will not stop everyone. A disciplined operator gets through, and I will come back to that. But they raise the attacker's cost and catch the high-volume, low-effort operators that scalable controls are best positioned to stop. This post is about moving that detection left of the laptop, and about why the work belongs to a program that spans recruiting, HR, and security rather than any single product you can buy. It is the defender's side of a shift I have written about from the candidate's side in The Trust Decay: hiring has quietly become an adversarial system.

## Why your background check is lying to you

A background check verifies that an identity is real and unblemished. It does not verify that the person doing the work is that identity. Those are two different claims, and the space between them is the entire business model.

These operations run on real US identities, either stolen or rented from a willing American. The SSN traces. County records are clean. Employment history, where it was ever real, holds up. Every field on the screening report goes green because the paperwork describes a real, law-abiding person. That person is simply not the one on the video call, and frequently not the one at the keyboard.

So the first rule: a clean background check proves the identity is clean, and nothing more about the person using it.

## How the operation works

DPRK IT workers pose as US-based remote engineers to route hard currency to a sanctioned regime. Three mechanics matter for defense:

- A US-based facilitator runs a ["laptop farm"](https://www.justice.gov/opa/pr/two-north-korean-nationals-and-three-facilitators-indicted-multi-year-fraudulent-remote). Your laptop ships to a real American address, someone installs remote access, and the operator drives it from overseas while the traffic looks domestic.
- One identity is often reused across several employers, sometimes simultaneously. That reuse is a weakness you can exploit: a bust or a burned persona at one employer can surface the same worker at the others, which is sometimes how a company learns it was hit at all.
- The person who interviews may not be the person who works, and neither has to be the name on the I-9.

You do not need to be a defense contractor to be a target. The [FBI has warned](https://www.ic3.gov/PSA/2025/PSA250123) that these workers have hit US businesses broadly, so if you hire remote engineers, assume you are in scope.

## The laptop is a one-way door

Before you ship hardware, you hold cheap, high-leverage controls. You decide who to talk to, how to verify them, and where to send equipment. After you ship, you have handed an unknown party a trusted endpoint and moved the whole problem onto EDR, SIEM, and the hope that the operator slips. The door is not literally irreversible: you can still contain the machine, reimage it, and revoke its sessions and secrets. What flips is the economics. Before shipment you prevent cheaply. After it you pay to contain.

Reframe shipping the laptop as a gate, and give it the seriousness you would give to granting production access. Nothing crosses that line until identity is established to a standard you would be willing to defend in an incident review. Everything below is about earning the right to ship.

## The program: gates and owners

The failures happen across recruiting, HR, IT, and security, so no single team can close them. Give each gate an owner and a written standard.

One thing to set before the gates: no single signal is a verdict. A VOIP number, an odd address, a fumbled local-knowledge question, or a VPN ASN each has an innocent explanation. What matters is the combination of independent inconsistencies. The program's job is to define when those inconsistencies trigger additional verification, who is allowed to make that call, and what evidence gets retained. Treat everything below as an input to that process, not a judgment about a person. This is hiring treated as an observability problem, which I argue more broadly in The Discovery Layer Is Broken.

**Recruiting gate.** Owned by recruiting, running a security-provided checklist.

- Camera on for every round. Treat "broken camera" and audio-only as signals worth pausing on.
- Force live, unscripted action. Hold the ID next to the face, turn to profile, put a hand in front of the face, run a live coding exercise instead of a take-home. As of 2026, real-time face swaps still commonly break on occlusion and profile turns, but treat that as a filter for low-effort operators, not a dependable break: higher-end tools increasingly pass the hand-across-face test. The durable value is forcing live variation the operator cannot pre-render, not the occlusion itself.
- Probe local knowledge casually: the weather right now, the nearest major airport, something a resident would know without thinking. Answers that fight the claimed time zone are a tell.
- Check persona hygiene: VOIP-only numbers, a two-week-old LinkedIn with forty connections, a headshot that surfaces on reverse image search, and near-duplicate resumes across separate candidates.

**Verification gate.** Owned by HR and recruiting.

Independent employment verification through published main lines, never a number the candidate hands you. In my experience this is the control most teams quietly skip, and it is the one that catches fabricated histories and "references" that ring a co-conspirator. One honest caveat belongs here: verification usually reaches only the previous employer, since candidates withhold consent to contact where they work now.

**Identity-assurance gate.** Owned jointly by security and HR.

Tie the same live human to the same government ID at three separate points: the interview, the I-9, and day one. Use an authorized representative or a notary for in-person document inspection, and make sure that inspector is employer-designated and independent, not chosen by the candidate, because a candidate-selected notary defeats the whole point. Even a clean inspection only proves a live person held a valid ID, not that that person is the one who will do the work. Run E-Verify, and remember it passes valid stolen SSN and name combinations, so treat it as a floor.

**Logistics gate.** Owned by IT. This is the last checkpoint before the one-way door.

Ship only to the identity's verified residential address, signature required, cross-checked against the address on file. Be clear-eyed about what that does and does not buy you. A clean address match proves nothing against the facilitator model, because the facilitator's real home is the address on file, and the laptop ships straight into the farm. What the gate catches is the reroute. A request to send the laptop to a different address, a freight forwarder, or a mail drop is one of the strongest single tells in the funnel. Refuse "I will use my own device" and "let me start before the laptop arrives."

## What actually happened, and what it proves

At one organization I worked with, a hire cleared the interview loop, the identity checks, and onboarding without a single flag. The catch came on day one, for the least sophisticated reason imaginable. He started a remote-access tool as root, and his sessions egressed through a rotating set of commercial VPNs in Western Europe, with the occasional US residential IP mixed in. EDR did its job, and the machine came off the network within hours. But containment is not prevention. The same day proved the endpoint controls worked and that identity assurance had let an untrusted operator reach a managed endpoint in the first place. None of those indicators are DPRK-specific; they are generic untrusted-operator markers, and foreign commercial-VPN egress is the opposite of the domestic-looking traffic a mature laptop farm produces. Treat the story as illustrative of the access pattern, not as attribution.

I share it as a warning rather than a win. Every front-door control in place was defeated, because a real US facilitator can appear on camera, pass the I-9, and receive the laptop at a genuine address before handing remote control to an operator overseas. One [convicted facilitator](https://www.justice.gov/usao-dc/pr/arizona-woman-sentenced-17m-it-worker-fraud-scheme-illegally-generated-revenue-north) ran a home laptop farm at the center of a scheme that placed workers at more than three hundred companies, with some of the hardware shipped onward overseas. When a live person fronts the identity, your pre-laptop program passes cleanly, the laptop ships, and you are left betting on the operator being careless.

He was careless. The next one will not be. A disciplined operator runs a KVM-over-IP appliance that presents to the operating system as a keyboard and a monitor, so there is no remote-access process to detect, and routes traffic through a US residential proxy that geolocates cleanly. None of the signals that made this catch would fire.

## The runtime backstop, for the ones who get through

Assume some will clear the front door, and build the net accordingly. The net cannot depend on the local network: a disciplined operator sanitizes the segment, so a subnet scan pushed through your EDR may see an empty, curated view. The inverse is worth knowing too - a residential LAN noisy with corporate devices from several different companies is exactly the farm signature the careless tier leaves lying around. Either way, point the sensors at what you actually own:

- Remote-access tooling on the endpoint (TeamViewer, AnyDesk, RustDesk, and the rest), at higher severity when it runs elevated or lands in a new hire's first weeks.
- USB and HID telemetry for unexpected device changes and unusual hardware profiles. The KVM appliance described above presents as an ordinary keyboard, mouse, or display and can spoof standard vendor IDs, so treat this as supporting telemetry, not a reliable KVM detector. It gives you a lead, not proof.
- Egress anomalies: non-US geolocation or VPN and hosting ASNs from a device that should leave the internet through a US home connection.
- Interaction latency, measured at the endpoint (research-grade). A remote-desktop or KVM channel inserts a round trip that surfaces as delayed reaction to on-screen events, and adds network jitter that shows up as variance in keystroke timing on the device itself. Two caveats keep it honest: it is endpoint-side only, not network RTT to your services (a US-local laptop or residential proxy tells your servers nothing), and it is far too noisy to stand alone, so it can corroborate other signals but never drive a decision.

Expect some of these alerts to be your own people. [Every Alert Is Your Alert]({filename}every-alert-is-your-alert.md) covers closing the true positives your own IR tooling generates, after I watched it trip the very EDR it was working alongside.

Wrap all of it in a heightened-monitoring window for the first thirty days of any remote hire. That is when these signals clustered, in the case I worked and in the public reporting, and it is the cheapest place to spend the attention.

## Do not make the laptop the last gate

The case above proves some operators clear every pre-shipment control, so the laptop should not be the final trust decision. Treat the first thirty days as a trust-establishment period, not just a monitoring window. A new remote engineer starts constrained: no standing production access, step-up approval for sensitive repositories and secrets, tighter SaaS entitlements, risk-based re-authentication, heightened logging. Access expands as the role actually requires it, earned rather than granted at onboarding. This assumes IdP and entitlement tooling mature enough to express it; the minimum viable version is manual - no standing production access, and a human approving sensitive grants for the first thirty days. This is blast-radius thinking applied to the identity layer, the same argument I make for [IAM permissions]({filename}iam-blast-radius-architecture-problem.md). You cannot prove a hire is legitimate before they start. What you can do is avoid making one irreversible trust decision, and increase trust only as the signals you control keep checking out.

## Do not build a discrimination engine

This is where a program keeps or loses its legitimacy. Screen the fraud, not the person. Detect on behavior and fraud markers, never on accent, name, national origin, or a vague sense that someone "seems foreign." That line is an ethical and legal requirement, and it also happens to be better security. Nationality is a terrible feature. It buries you in false positives, it is trivial to spoof, and it trains your team to wave through the domestic-sounding facilitator, which is precisely the profile that clears every gate in the case above. Write the criteria down, make them reviewable, and keep a human in the loop on every adverse decision.

## If you do only three things

- Independent employment verification on published lines. In my experience the highest-yield cheap control against low-effort operators.
- Verified-address-only shipping with a required signature. Make the laptop a gate.
- A thirty-day heightened-monitoring window on new remote hires. Your backstop for the ones who clear the door.

The alert in your SIEM is the sound of a control that fired too late. Move the decision to the day before the laptop ships, make it someone's job, and design everything after it on the assumption that a good operator gets through anyway.
