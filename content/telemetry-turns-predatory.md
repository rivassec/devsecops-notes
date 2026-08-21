Title: When Telemetry Turns Predatory: A DevSecOps Look at Digital Repression in Venezuela
Date: 2026-08-25
Status: draft
Author: Oliver Rivas
Category: DevSecOps
Tags: devsecops, security, venezuela, censorship, threat-modeling, privacy, surveillance
Slug: telemetry-turns-predatory
Og_image: images/og/telemetry-turns-predatory.png
Summary: Every SOC pipeline has a shadow version. Using Venezuela as a grounded case study: how the primitives security engineers build become surveillance systems.

Every Security Operations Center follows a familiar pattern: collect telemetry, correlate identities, prioritize signals, and trigger a response. Security engineers build these pipelines to defend infrastructure. The same architectural primitives, however, are inherently dual-use.

This article examines publicly documented events in Venezuela through the perspective of a DevSecOps engineer.

## A personal note

I have a personal stake in this analysis. I was born in Venezuela and left the Gran Caracas region at eighteen. I still have extended family there. I have also, in more than two decades since I left, been on the receiving end of the [regime's information apparatus]({filename}/venezuela-twitter-proxy-osint-final.md) in ways that are not the subject of this piece. What I write below is not a policy essay - it is what a security engineer sees when he or she watches, over the course of many years, the slow convergence of a state and its telemetry. The technical patterns are familiar to anyone who has designed a SIEM, an identity provider, or an EDR pipeline. That familiarity is the point.

## Two pipelines, same primitives

Enterprise security tooling is not the problem. The problem is what the same collection, correlation, and prioritization patterns become when the customer is coercive power. The same pipeline shape appears in both columns below; only the governance model around it changes.

```text
          Enterprise SOC                Venezuela Case Study

  Endpoint                         Citizen
      |                                |
  Telemetry                        Online Activity
      |                            Civic-App Reports
      |                            Network Metadata
      |                                |
  SIEM                             Data Collection
      |                                |
  Identity Correlation             Identity Correlation
      |                                |
  Alert Prioritization             Operational Prioritization
      |                                |
  Incident Response                Enforcement Action
```

## Methodology

**Observation** refers to findings documented by credible public sources.

**Engineering interpretation** refers to analysis through the lens of cloud security, DevSecOps, and threat modeling.

## What the public evidence shows

### Electronic Frontier Foundation (EFF)

**Observation**

EFF's [*Unveiling Venezuela's Repression: Surveillance and Censorship Following July's Presidential Election*](https://www.eff.org/deeplinks/2024/09/unveiling-venezuelas-repression-surveillance-and-censorship-following-julys) and [*Unveiling Venezuela's Repression: A Legacy of State Surveillance and Control*](https://www.eff.org/deeplinks/2024/09/unveiling-venezuelas-repression-legacy-state-surveillance-and-control) document the evolution of VenApp after the 2024 presidential election and broader patterns of digital repression.

**Engineering interpretation**

Viewed as a system, VenApp is a citizen-scale SIEM. The ingest layer is a mobile client; the events are user-attributed reports of "suspicious" behavior; the natural entity-resolution layer for those reports is the state identity infrastructure EFF documents as weaponized against the population - the Carnet de la Patria and Sistema Patria apparatus - joining a report to a person through national-ID and phone records the state already holds, the same shape as an enterprise correlation against email, SSO subject, and device ID. Any engineer who has built a Splunk ingest pipeline, an Elastic detection rule, or a Sumo Logic content pack recognizes the pattern immediately. Normalization, field extraction, correlation, alert scoring, case creation - these are the same stages that turn raw logs into an IR ticket for a credential-stuffing attempt in an enterprise SOC. The difference is not architectural. The difference is who the tenant is, what the tenant treats as a "threat," and what happens at the response stage. In one pipeline the response is an account lockout and a support ticket. In the other, the response is physical.

### Freedom House

**Observation**

[*Freedom on the Net 2025: Venezuela*](https://freedomhouse.org/country/venezuela/freedom-net/2025) documents expanded blocking of websites and communications platforms during and after the July 2024 election, the Operación Tun-Tun mass-arrest campaign, and arrests connected to online activity. EFF separately documents authorities stopping people to check the content of their phones and detaining those whose devices hold anti-government material.

**Engineering interpretation**

Operación Tun-Tun is what happens when endpoint detection and kinetic response merge into a single workflow. In an enterprise EDR context - Falcon, SentinelOne, Defender - an alert produces a ticket, a triage step, and typically at worst a device quarantine. The kinetic parallel exists (physical security escorting a compromised laptop off-site) but it is rare and tightly scoped. In the Venezuelan case, the same alert-to-response loop is compressed and applied at population scale: an online post, a phone-content inspection of the kind EFF documents, and an arrest can function as stages of a single pipeline whose escalation path is physical. From a threat-modeling perspective, the transformation is not "surveillance was added." The transformation is that the response stage of an ordinary detection pipeline was rewired to enforcement rather than remediation.

The primitives were already in place.

### VE Sin Filtro

**Observation**

[VE Sin Filtro](https://vesinfiltro.org/), using [OONI](https://ooni.org/) measurement methodologies, documents DNS manipulation, IP blocking, SNI filtering, interference with public DNS resolvers, and blocking of circumvention tools across multiple ISPs.

**Engineering interpretation**

VE Sin Filtro's measurement work, built on OONI Probe, documents what interference actually looks like on the wire. Their report on the 2024 presidential election (published March 2025) documents DNS manipulation on CANTV, Movistar, and Digitel - Venezuela's three dominant ISPs - against independent media domains, along with IP and HTTP/HTTPS blocking and interference with public resolvers such as 1.1.1.1 and 8.8.8.8 that would otherwise route around the manipulation. Read from the defensive side, those block categories map onto techniques I have configured or debugged directly: DNS responses rewritten so a censored domain resolves nowhere useful; SNI-based filtering that reads the hostname in the TLS ClientHello and drops the handshake to a policy-blocked destination; WAF and firewall ACLs that block by IP or CIDR; DNS Response Policy Zones and Cloudflare Gateway doing the same against malware. The mechanism is identical. Only the block list differs.

What VE Sin Filtro adds beyond policy reporting is a reproducible measurement methodology, which is what turns "the internet feels broken today" into an evidence-based finding that survives cross-checking.

## Every security capability has an abuse case

This is the weaponization exercise from the next section, run against the primitives already in play. The first four rows are visible in the Venezuelan record; the last two are the same logic extended to capabilities every SOC already runs.

| Security Capability | Enterprise Security Use | Potential Abuse |
|---|---|---|
| SIEM | Detect intrusions | Monitor political activity |
| DNS filtering | Block malware | Block independent media |
| Endpoint telemetry | Incident response | Citizen surveillance |
| Identity systems | Access control | Population tracking |
| Audit logs | Compliance and forensics | Behavioral profiling |
| Geolocation | Fraud detection | Movement monitoring |

## Security engineering lessons

The value of the Venezuelan case study for a security engineer is that it exposes an assumption embedded in most threat models: that the operator of the pipeline is the good actor. The moment that assumption becomes optional, every design decision changes. Three practices follow.

**1. Add a Weaponization section to every design review.**

Standard threat modeling frameworks largely assume an adversary attacking from outside the system. Even LINDDUN, which treats the operator's own data processing as a privacy threat source, does not model the case where the legitimate operator turns the full detection-and-response pipeline against its subjects. Add a fourth question to every design doc: *If an authoritarian tenant owned this pipeline, what would they do with it?* For every data flow you draw, write one sentence describing the weaponized use case. The exercise is uncomfortable, which is the point.

A minimal template lives at [github.com/rivassec/weaponization-threat-model](https://github.com/rivassec/weaponization-threat-model). It provides a one-page addendum to a standard STRIDE doc: for each data element, the authoritarian-tenant reading; for each retention decision, the subpoena-inversion reading; for each correlation-key choice, the population-tracking reading. Adopt it, fork it, or replace it. The specific artifact matters less than the commitment to run the exercise.

**2. Treat metadata as content.**

Encryption of message bodies is now table stakes. Metadata - who talked to whom, when, from where, on which device - is often left in plaintext, retained by default, and joined against identity systems. In the Venezuelan case, metadata alone would be more than sufficient to prioritize enforcement. In your systems, metadata is more than sufficient to reconstruct behavior, relationships, and identity. Log the least metadata your product can function with, and retain it for the shortest window your compliance obligations allow. Ask this question the way you would ask about a security bug: not "is this useful to have?" but "is this dangerous to have?"

**3. Design as if governance will change.**

The tools you build outlive the leadership that scoped them. The privacy commitments made by a founding team cannot be relied on to bind the acquirer, the successor board, or the government that subpoenas the resulting system. Retention sunsets should be the default, not the exception. Owner-change reviews - what happens to this pipeline if the executive who scoped it leaves, if the company is acquired, or if a nation-state compels access - should be a scheduled part of your design cadence. This one I have practiced as a habit but not yet built into tooling; I raise it in design reviews and it lands or it doesn't, depending on the room. It should be built into the process instead.

I write "should be" because I have seen the shape of what happens when it isn't. Some years ago, I was part of a rollout at a large communications platform of a feature that required users to verify a phone number to keep certain account functions. I raised the abuse concern internally: in jurisdictions where pseudonymous accounts were the only safe way for activists to organize, a phone-verification requirement was going to be a state's dream - a real-name join key against every account operating under a handle. The escalation went to the appropriate teams. It was denied. Later, activists in one of the affected jurisdictions were arrested, and some did not survive their detention. I did not sleep well for a long time after that decision was made. I know correlation is not causation, and I do not know whether the verification requirement contributed to those arrests - I am not claiming it did. I include this because the shape of the harm is what security engineers need to sit with, not because I claim to know its exact mechanism. It informs how I write every design review now.

## Caveats

Internet censorship measurement is inherently difficult, and the sharpest limitation in this analysis is attribution. The network measurements demonstrate that DNS, IP, and TLS-layer interference occurred, but they do not by themselves prove central coordination versus independent per-ISP compliance. The internal architecture of systems like VenApp is inferred here from observable behavior, not from documented internals, and I have flagged those inferences as interpretation rather than fact throughout.

## References

[1] Laura Vidal and Jillian C. York. [*Unveiling Venezuela's Repression: Surveillance and Censorship Following July's Presidential Election*](https://www.eff.org/deeplinks/2024/09/unveiling-venezuelas-repression-surveillance-and-censorship-following-julys). Electronic Frontier Foundation. September 16, 2024.

[2] Laura Vidal and Jillian C. York. [*Unveiling Venezuela's Repression: A Legacy of State Surveillance and Control*](https://www.eff.org/deeplinks/2024/09/unveiling-venezuelas-repression-legacy-state-surveillance-and-control). Electronic Frontier Foundation. September 18, 2024.

[3] Freedom House. [*Freedom on the Net 2025: Venezuela*](https://freedomhouse.org/country/venezuela/freedom-net/2025).

[4] VE Sin Filtro. [*Reporte Redes de Control: Censura y represión digital en las elecciones presidenciales en Venezuela*](https://vesinfiltro.org/noticias/2025-03-12-reporte-elecciones-presidenciales/). March 2025.

[5] [OONI Documentation](https://ooni.org/).

## Conclusion

The technology discussed here is not unique to Venezuela. It is the same telemetry, the same identity graphs, the same pipelines we build in every SOC on every continent. What changes is who operates them and against whom.

The question I want you to carry into your next design review is no longer only *is this design secure?* It is *who does this design protect, and who does it expose?*

I think about the systems I design now knowing that somewhere in the Gran Caracas region, my family is inside systems built with the same primitives. I suspect every security engineer has a version of this thought waiting for them, whether or not they have noticed it yet.
