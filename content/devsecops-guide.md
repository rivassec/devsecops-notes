Title: The DevSecOps Guide: Hardening, IAM, and Incident Response
Date: 2026-08-15
Category: DevSecOps
Tags: devsecops, security, iam, kubernetes, incident-response, tls
Slug: devsecops-guide
Og_image: images/og/devsecops-guide.png
Author: Oliver Rivas
Summary: A hub for the DevSecOps writing on rivassec.com: IAM blast radius, TLS, incident response, and controls that hold up in production.

<!-- TODO: expand intro - flesh out the narrative framing for each cluster
     (IAM, cryptography/TLS, incident response, adoption-as-control) and add a
     short "start here" recommendation for new readers. -->

This is the hub page for the DevSecOps writing on rivassec.com. The posts below
share one throughline: security controls only matter if they hold up under real
operational pressure - the day a role is assumed at scale, the moment an alert
fires against your own tooling, or the 208th day of uptime.

## Identity and Access

- [IAM Blast Radius Is an Architecture Problem, Not a Policy Problem](iam-blast-radius-architecture-problem.html)
- [IAM Roles That Fail Loud: Small Defaults, Big Difference](iam-safe-defaults-fail-loud.html)
- Interactive: [IAM Blast Radius analyzer](/tools/iam-blast-radius/) - paste an IAM policy, see its potential blast radius in your browser

## Cryptography and Transport

- [TLS Has Three Jobs. Forget the Rest.](tls-three-jobs.html)
- [Elasticsearch Snapshot Verification, Minimal Privileges](elasticsearch-secure-snapshot-verification.html)

## Operating Under Pressure

- [The 208.5-Day Kernel Bug: Uptime, Overflow, and Risk](208-day-kernel-bug-lessons.html)
- [Taming the OOM Killer: Process Priorities on Linux](oom-killer-process-prioritization.html)
- [Bandit-Clean Pwnagotchi Plugins: How subprocess Goes From Risk to Routine](pwnagotchi-plugin-bandit-hardening.html)

## Program and Adoption

- [Adoption Is a Security Control: Notes from Paving a Road](paved-road-adoption-as-control.html)
- [The Discovery Layer Is Broken: Hiring as an Observability Problem](hiring-discovery-layer-broken.html)
- [The Trust Decay: Why Modern Hiring Has Become an Adversarial System](trust-decay-adversarial-hiring.html)

## AI Security and Threat Intelligence

- [When the Output Carries the Signal: Claude, SynthID-Text, and the New Detection Attack Surface](claude-synthid-text-watermark-attack-surface.html)
- [Prompt Injection Will Become a Supply Chain Evasion Technique](prompt-injection-supply-chain-evasion.html)
- [Catching a Nation-State Proxy: OSINT on Twitter](venezuela-twitter-proxy-osint.html)
