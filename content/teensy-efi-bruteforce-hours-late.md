Title: The Teensy That Failed in Public: An EFI Brute Force, Hours Late
Date: 2026-05-21
Modified: 2026-05-21
Category: Projects
Tags: hardware, mac, efi, teensy, security-research, hackaday, hacker-news, open-source
Slug: teensy-efi-bruteforce-hours-late
Authors: RivasSec
Summary: In 2013, Hackaday wrote that my MacBook EFI brute force was unsuccessful. Hours after the article shipped, it worked. Three rate-limiting defenses, each leaking information at a different observable seam — the same pattern that shows up daily in modern cloud security architectures. A reread of the project that survived me, plus the invariant that ports cleanly into 2026 work.
Cover: images/covers/teensy-efi-bruteforce-hours-late.png

Most security defenses are layered. Each layer is built around a model of who attacks it, how fast, and through which surface. The seams between those layers — where one defense ends and the next begins — are where the threat model assumed an attacker would not be. Which is also where the information leaks live.

In February 2013 I built a Teensy-based brute force against the EFI password on a 2012 MacBook Pro I owned. The naive version did not work. The version that did work was the one that treated three independent rate-limiting defenses as three independent observation points. Hackaday had already published the story under the headline "[Mac EFI PIN Lock Brute Force Attack (unsuccessful)](https://hackaday.com/2013/02/26/mac-efi-pin-lock-brute-force-attack-unsuccessful/)" by the time the working version landed. The headline never updated. The repo is still on GitHub at [efi-bruteforce](https://github.com/rivassec/efi-bruteforce) thirteen years later. The hardware bug it exploits has been dead since the T2 chip in 2018.

The technique was not the interesting part. The interesting part was that three independent rate-limiting defenses each leaked information through a different observable edge, each was defeatable with a different countermeasure, and none of them coordinated with each other. That is the same shape most cloud security architectures still have in 2026.

This is the post-mortem the original Hackaday article should have linked to. It is also the lens I use now when I evaluate layered cloud security designs.

## The setup

A 2012 MacBook Pro I owned. I had wiped the drive with `dd` from another machine because that was the cleanest way to do a full overwrite. When I booted it back up, the firmware presented a six-digit EFI password prompt I had set months earlier and forgotten.

The supported paths were:

- Reset NVRAM by pulling RAM. Worked on older Macs. The 2012 unibody had a dedicated `ATMEL 1123 TINY13V 10SU` chip storing the password independently of NVRAM, so RAM swaps changed nothing.
- Apple Support with proof of ownership. They generated a per-machine reset hash from a 33-character identifier the firmware would surface with a specific key combo. Slow.
- SPI flash reprogram. Risk of bricking a $2,000 laptop.

I went with option four: a Teensy 3.2 emulating a USB keyboard. The naive sketch is ten lines. It does not work. The interesting work is in why each defense layer announced itself.

![Teensy 3.2 attached to a 2012 MacBook Pro showing the EFI password prompt with a four-digit PIN entry field]({static}/images/teensy-efi-bruteforce-rig.webp)

## Three layers, three observable edges

**Layer 1: USB poll-rate limiting.** The firmware polled the USB bus at intervals appropriate for human input. Sending faster than that interval dropped keystrokes silently. The leak was timing — the firmware's behavior was visibly different at fast input speed than at slow input speed, and the difference was observable from outside. Fix: `delay(450)` between presses, longer delays after Enter.

The cloud-security analog is API rate limits that return 429 versus silent throttle versus 200-with-partially-applied-results — three distinct outputs from one input class, each leaking information about which limiter is active. Most production rate limiters announce themselves in at least two of those modes. The combination tells you which layer you are talking to.

**Layer 2: per-attempt rate-limiting.** After the timing fix, the brute force ran cleanly through the 4-digit space (10,000 PINs) over ~48 hours. The machine remained locked. Some threshold of consecutive incorrect attempts had silently transitioned the firmware into ignore-mode. The screen kept showing the password prompt. Keystrokes appeared to register. Nothing was actually being checked. The leak here was the absence of a leak — the system stopped responding while pretending to respond. Fix: power-cycle every N attempts, persist the current PIN index via EEPROM, resume.

The cloud-security analog is OIDC token validation gaps where signature checks pass but claim validation silently no-ops on certain edge cases. The system reports success with a token that means nothing. Same shape: the response signal becomes meaningless once a hidden state transition has happened, and only timing or external-state inspection reveals the transition.

**Layer 3: public correction lag.** The Hackaday article ran with the failure framing because that was true at press time. By the time the article had been live for hours, the brute force was working. The corrected version lived in a quiet repo update. The article never followed. Years later the failure narrative was still the canonical version in search results.

The leak here was social, not technical. Public failure stories propagate faster than public corrections. The cloud-security analog is post-incident write-ups: the initial RCA spreads, the deeper post-mortem rarely catches up, and the institutional learning compounds against the wrong version of the story. Building the discipline to surface the corrected version louder than the initial one is part of senior security work.

Three layers. Three observable edges. Each defeatable with a different countermeasure. None of them coordinated with each other to detect that all three were under attack from the same source. That is the part that ports.

## Why this stopped working

Apple killed this entire class of attack with the T2 chip in 2018 and Apple Silicon in 2020. The firmware password now lives in a hardware enclave that validates submissions in the secure enclave (not the firmware), enforces rate-limiting at the hardware level with no observable distinction between "wrong" and "ignored," and does not expose a USB HID-controllable input path to the password prompt at all.

The Teensy code does nothing useful against modern hardware. Apple shipped the right fix. The repo stays up because the technique is reproducible on legacy hardware (digital forensics, device recovery on hardware you legitimately own), the timing values are documented in the sketch, and old security write-ups are useful as teaching artifacts. None of it is a current exploit.

## What happened to the project after I stopped paying attention

I forgot about the repo for a while. The community did not.

The first downstream wave landed on MacRumors. A 200-plus-page thread on EFI unlock methods turned the project into a reference implementation. Page 9 alone references my old `orvtech` handle 43 times. Quotes:

> "Big up to orvtech who built a small brute force kit using the Teensy 3."

> "Let us know how you get on with orvtech's code."

> "Orvtech, can you help with a sketch or coding which includes the 5 mins wait after 5 attempts."

I posted in that thread, helping people debug their ports against different MacBook generations and password-prompt screens. People treated the code as canonical and asked me to extend it for cases I had not built for.

I built one of those extensions: a follow-up project against the iCloud Activation Lock 4-digit prompt, a separate screen Apple introduced for stolen-device deterrence. The original writeup is in the [Wayback Machine](http://web.archive.org/web/20191118170802/https://orvtech.com/ataque-fuerza-bruta-pin-icloud-en.html) since I let `orvtech.com` lapse. That iCloud variant is what got picked up by [knoy/iCloudHacker](https://github.com/knoy/iCloudHacker), which has accumulated 222 stars and 72 forks of its own.

In July 2014 the project hit Hacker News with [67 points and 14 comments](https://news.ycombinator.com/item?id=7993435). The HN crowd had useful additions: an EEPROM programmer would be faster than a brute force; some newer models stored passwords in TPM that could be cleared in-circuit; the entire class of attack had been a quietly-known industry secret for years. The HN comments are more thorough than my original writeup.

In May 2015 the [Arduino Forum titled a thread](https://forum.arduino.cc/t/revisiting-orvtechs-efi-firmware-icloud-unlock-for-macs/313576) "Revisiting orvtech's EFI Firmware & iCloud unlock for Macs." Three months later, Charlie_turner posted a working Pro Micro port with LCD support under Apache 2.0. A Spanish-language blog at iivanmendozaa.blogspot.com had translated the writeup the prior year and added LCD documentation for a Latin American audience.

I did not moderate any of this. I did not accept pull requests, coordinate the downstream ports, or even watch the threads consistently. The project went on without me — in three languages, on at least three hardware platforms, against two distinct password-prompt screens, with one fork eventually outgrowing the original repo by an order of magnitude in stars.

Most projects published under MIT die in obscurity. This one survived because three properties stacked. The README named the failure modes, not just the success path — future contributors knew where the rate-limit edges were because I had written them down while I was finding them. The timing values were tuned and inline in the source — anyone porting could see why a specific delay was the value that survived contact with that specific firmware. The license made the genealogy traceable — when knoy's fork outgrew the parent, the line of descent stayed visible.

A project that ships only the working configuration is opaque to future contributors. A project that ships the boundary is teachable. The teachable one survives.

## The invariant

The reason this thirteen-year-old hardware project still informs how I think about cloud security is one principle:

**Layered defenses leak information at the seams between layers, not at the layers themselves.**

Each individual layer in the EFI password system was reasonable. Polling rate-limiting is a reasonable defense against human typing speed. Per-attempt rate-limiting is a reasonable defense against repeated guesses. After-N silent-ignore is a reasonable defense against the attack continuing past a threshold. The compromise was that the three layers operated independently, each with an externally-observable signature, with no shared state about whether all three were under attack from the same source.

Modern cloud security has the same shape. WAF in front of API gateway in front of application in front of database, each with its own rate limiter, its own logging, its own threat model, none of them sharing the question "is this same actor probing all four of us." The independent-defense pattern is the failure mode, not the controls themselves.

Three implications I apply to the work I do now:

**Audit the seams, not the layers.** When I review a security architecture today, I am not asking "is the WAF tuned correctly." I am asking "what does the WAF know that the API gateway does not, and where does an attacker exploit the gap." Same for IAM trust policies between accounts, same for CI/CD trust between repo and runner, same for cross-cloud federation.

**The absence of a response is a response.** The EFI firmware's silent ignore-mode taught me to instrument for "what is the system not doing right now" alongside "what is the system doing." This shows up daily in cloud work — failed-but-silent S3 puts, K8s admission controllers that drop requests without logging, CI workflows that skip steps under specific conditions. The interesting failures rarely throw exceptions.

**Independent throttles compound badly.** When three layers each rate-limit separately, an attacker probing all three sequentially has three budgets. The architectural fix is shared rate-limiting state, which is operationally expensive and almost never deployed. Knowing that this trade-off is being made — even silently — is more useful than pretending the multi-layer rate-limit budgets add up.

## Where this class of problem lives in 2026

Three places I would point a junior security engineer at right now if they wanted to see the same shape:

**CNAPP product seams.** Cloud-native application protection platforms bundle CSPM, CWPP, CIEM, and IaC scanning into one product. Each was a separate product five years ago. The bundling is operational convenience. The seams between the four sub-engines are where misconfigurations now hide — typically because the data model assumes the engines see the same view of the cloud account, and they often do not. A wildcard IAM policy may surface in CIEM but not CSPM, or in CSPM-on-account-A but not CSPM-on-account-B-during-Org-migration.

**Agentic system rate limits.** AI agents that call tools have rate limits at the model layer, the tool-registry layer, and the downstream API layer. Each layer's limit is reasonable. The composition is not. An agent that fails fast at the model layer can saturate downstream APIs by retrying through alternate tool paths. This is the EFI three-layer pattern reborn at the agent-orchestration level, and the controls for it are still being designed.

**Cross-cloud trust boundaries.** A workload running in one cloud authenticating to a service in another cloud passes through three or four trust validation layers — federated identity provider, target cloud's IAM, target service's resource policy, sometimes a network policy. Each layer trusts the previous to have validated correctly. Most attacks against this architecture exploit the layer that quietly accepted a token the previous layer should have rejected. The seams compound.

## What I would have done differently

Three corrections, framed as transferable instruction rather than personal regret:

**When public failure goes viral, public correction has to follow loud.** I let the Hackaday "unsuccessful" headline stand for years while the working code lived in commits. The follow-up post is the discipline. This applies inside organizations too: when an incident write-up goes wide and the deeper analysis lands later, the deeper analysis needs to be republished as if it were the first version, not appended as a footnote.

**Document the most interesting finding in the README, not in a comment reply.** The Atmel chip purpose-built to defeat the NVRAM-reset workaround was the most useful thing I learned in the entire project. It sat in a forum reply for years because I did not recognize it as the headline. If a finding is what would make your future self glad you documented it, it goes in the canonical artifact, not in conversation.

**Frame offense as defense.** "I brute-forced my own laptop" is a worse story than "Apple's EFI password works, here is the threat model that justifies the implementation, here is where it leaked at the seams, and here is why the modern version closes the leak by design." The defensive framing makes the same artifact useful to engineers building the next version. The offensive framing leaves it as a war story.

## What's at the same address

The repo is at [github.com/rivassec/efi-bruteforce](https://github.com/rivassec/efi-bruteforce) under MIT license. The README documents the timing values and the power-cycle workaround inline. If you are working with 2012-2017 MacBook hardware for legitimate forensic or device-recovery purposes, the code may still apply. Anything newer, the code does nothing for you, which is what Apple's hardware security model is supposed to do.

For the same instincts applied to current cloud work, [iam-safe-defaults](https://rivassec.com/iam-safe-defaults-fail-loud.html) is the closest cousin: a small library that makes the IAM policy decisions a future auditor will care about happen at write time, not at audit time. The shape is the same — make the boundary teachable, document where the seams leak, ship the artifact in a form that survives your attention.
