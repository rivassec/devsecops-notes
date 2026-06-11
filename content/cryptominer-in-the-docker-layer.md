Title: The Miner Was In The Image Layer, Not In Memory
Date: 2026-06-24
Modified: 2026-06-24
Author: RivasSec
Category: DevSecOps
Tags: incident-response, docker, overlay2, cryptominer, guardduty, aws, forensics
Slug: cryptominer-in-the-docker-layer
Summary: GuardDuty said the host was mining. `ps` and `ss` came back clean. The miner was hiding one layer lower, baked into the image's overlay2 diff directory and re-dropped on every container restart. A walk through the IR sweep that almost called it a false-positive.
Cover: images/covers/cryptominer-in-the-docker-layer.png
Status: draft

[TOC]

GuardDuty fired several findings on a production EC2 instance in quick succession. Two `CryptoCurrency:Runtime/BitcoinTool.B!DNS` against the host and against a container on the host, one `CryptoCurrency:EC2/BitcoinTool.B!DNS` from the VPC DNS resolver, and an `AttackSequence:EC2/CompromisedInstanceGroup` correlating the others into one critical-severity event. The destination was `auto.c3pool.org`, a public Monero pool. The instance was a Flink job server.

I opened an SSM session onto the host, ran `ps -ef` inside the container, ran `ss -tunap`, and found nothing. No miner process. No outbound connection to the pool. No CPU pressure. The Java heap looked normal. The Flink job manager was happily doing what Flink job managers do.

For a while I was sure I was looking at a false-positive.

I was not.

The miner was on disk, in one of the image's overlay2 layers. The container's filesystem could see it through the union mount, but the binary was not in the process space at the moment I checked, which is what `ps` reports. Every container created from this image had the binary on disk from instant zero, and the persistence lived in a layer that survives `docker compose down -v`. This post is about the sweep that found it, what I now know to look at on the next one, and what I am still not sure about.

## The shape of the alert

A modern GuardDuty IR loop has two tiers. There are the per-signal findings, which fire on a single observation: a DNS query to a known mining pool, an SSH brute-force attempt, a port scan against a sensitive port. They are designed for noise reduction. Most of them are individually low-confidence and will resolve as false-positive once a human looks.

Then there are the correlation findings. `AttackSequence:EC2/CompromisedInstanceGroup` is one of those. It does not fire on a single signal. It fires when GuardDuty has stitched together several signals into a coherent story: a brute-force from a known-bad IP, then a port probe from a different known-bad IP, then a process inside a container talking to a mining pool, all on the same instance, in the same window. The finding hands you the timeline pre-assembled.

Per-signal findings can be wrong. Correlation findings can be wrong too, but in my experience they earn priority because they pre-stitch the timeline and tend to carry the highest-confidence detail in the inbox. The lesson I keep relearning is to read them first, especially before declaring per-signal findings false-positive.

In this case the AttackSequence finding listed the file path on disk:

```
/opt/flink/.usr_gsdm/lib/systemdev/dns-filter
```

That string was in the JSON. Not a heuristic, not a prediction, a path. GuardDuty's runtime sensor had observed the binary executing and recorded its on-disk location.

That is when I went looking on the host.

## The path that mattered

The container view is not the host view. Inside the Flink job manager container, `/opt/flink/.usr_gsdm/lib/systemdev/dns-filter` resolves to whatever the overlayfs union mount makes visible at that moment. From the host, the same content lives in several overlay2 paths depending on what you are asking about. Two of them matter for this story.

The first one is the image's diff directory:

```
/var/lib/docker/overlay2/bed3ac13bfa4f2562f99ec7ec9f9be614371a16d6af056a66343cbb125b61b65/diff/opt/flink/.usr_gsdm/lib/systemdev/dns-filter
```

The second one is the merged view, which is what the running container actually sees:

```
/var/lib/docker/overlay2/bed3ac13bfa4f2562f99ec7ec9f9be614371a16d6af056a66343cbb125b61b65/merged/opt/flink/.usr_gsdm/lib/systemdev/dns-filter
```

These two paths are related but not equivalent, and the difference is the entire post.

The `diff` directory is a layer's contribution to the union. If you wrote a Dockerfile and `COPY`'d a binary into the image at build time, that binary lives in some layer's `diff` directory forever. When you `docker pull` the image, those files arrive on disk. When you `docker rm` the container they stay there, attached to the image, not to any specific running container. The only way to get rid of them is `docker rmi`.

The `merged` directory is the union view of all layers stacked together. It is what the container sees as its filesystem root. When the container runs, processes inside it read from `merged`. When the container stops, `merged` is unmounted, but the underlying `diff` directories remain.

The other two paths are `upperdir` (the writable layer the container can modify at runtime) and `workdir` (overlay's scratch space). I checked both. The malicious binary was in neither. It was in a lower layer's `diff` directory, the read-only foundation that came down with the image pull.

To make sure I had the layer role right, I cross-referenced against `docker inspect <container>`. The `GraphDriver.Data.LowerDir` chain on the running container included this directory in its read-only stack, which is what marks it as a build-time image layer rather than the container's writable upper. `docker history` told me the image had `COPY` steps in its build (which is unsurprising for a Flink image) but `docker history` shows the instruction, not the per-file provenance, so I am not claiming it identified `dns-filter` specifically. The shape of the evidence is "this layer is in the LowerDir chain, the LowerDir chain is read-only, the running container's writable space is empty for this path." That is enough to place the file in an image layer.

That distinction matters. A miner in the writable upperdir would be a runtime drop, written into the container after it started, possibly by a process inside it. A miner in an image layer means the image itself is the persistence mechanism. If that layer originated from the image (rather than from on-disk tampering, which I cover next), every container created from this image inherits the file at birth.

## What the binary did

The pattern I inferred (and want to flag as inferred, since I never finished reconstructing the execution chain) is that the binary ran shortly after container start, fired one DNS query to the pool, tried to start mining, and died before steady state. The Flink JVM was using almost all the cgroup memory and the miner could not get a foothold. By the time I looked, the process was not on the system anymore. GuardDuty's runtime sensor logged the execution and the DNS query each cycle; I did not pull the per-execution timestamps and process ancestry from those records before the host got rebuilt, so the precise launch path is something I am calling "consistent with container-start triggering" rather than proven.

This is why `ps` was empty.

The pattern repeated on every restart. The team had been bouncing the container hard for an unrelated stability issue over the prior couple of days. Each restart re-mounted the poisoned layer, the miner came up briefly, fired DNS, lost the resource fight, and died. GuardDuty's runtime sensor caught the DNS each time. The host-level `ps` view, sampled later by a human, missed it every time.

The binary itself is around 9.8 MB, owned by `flink` (uid 9999). SHA-256:

```
c3cedc9a4d761e9a96207ae93b92d5ca75ed304fecbedfdefa8a2d95b5b77997
```

I will note here that file mtimes inside an image layer are weak forensic evidence: tar archives can preserve build-host timestamps, `COPY` carries them across, and an attacker with write access can `touch` whatever they want. I am treating mtime as a clue, not as proof of when the file arrived on the host.

The path on disk uses a leading dot for the parent directory (`.usr_gsdm`) so a casual `ls` of `/opt/flink/lib/` does not show it. The binary is named `dns-filter`, which sounds plausible next to a real Flink deployment that does in fact filter DNS-shaped log entries. The disguise is decent. It is not great. It is exactly good enough to survive a reviewer who is glancing at file listings.

## Was the image poisoned at build time, or on disk?

This is where the post stops being a clean story.

The image had not been pulled in months. The malicious binary's mtime sat well after the last pull, by enough that no `docker pull` of this image happened in the interval.

That leaves two hypotheses.

One: the tag this deployment tracked was rewritten upstream to point at a different digest, and a fresh pull at some later point brought down a malicious layer. OCI digests are content-addressed and cannot be mutated in place, but tags map to digests and that mapping can be moved by anyone with push access to the repository. This is a supply-chain compromise of the registry, expressed as a tag rewrite that surfaces malicious content the next time someone resolves the tag.

Two: the image on this host was modified on disk after the pull. Some process on the host wrote into the layer's diff directory directly, with root or `docker`-group access. This is on-disk tampering, which means the attacker had host-level write access to `/var/lib/docker/overlay2/...` at some point.

I cannot tell which one happened from the data on hand. I compared the digest the host had recorded for this image against the digest the registry was currently advertising for the deployment's tag, and they matched. That tells you something narrow: the tag is currently mapped to the same digest the host pulled. It does not tell you whether the tag was *ever* pointed at a different digest in between. On-disk tampering remains possible too; it would require modification of Docker's layer storage and the corresponding metadata in `imagedb` rather than a simple file copy, but root on the host is sufficient.

This is unresolved. We prioritized containment and rebuild-from-clean over deep historical forensics, which is its own scope choice and one I'd make again with the same constraints. Most incident write-ups jump to attribution because attribution makes the story feel done, and the people who paid to read it want a beginning, middle, and end. The middle is "find the malware on disk." The end is "tell people how to find it." Attribution sits outside this scope.

There is a second gap I did not close before rebuild: the execution chain. I confirmed the binary executed and I confirmed it was on disk in an image layer, but I did not finish reconstructing what launched it. The candidates were the image's `ENTRYPOINT`, the Flink-specific bootstrap scripts shipped by the workload, an `LD_PRELOAD` in the image, a startup hook in the container's init system, or a sidecar I had not noticed. The image got rebuilt and the host got cleaned before I closed that loop. If I had to do it again with more time, the first thing I would walk is `docker inspect <image>` for `Entrypoint` and `Cmd`, then every shell script those reference, looking for the call that named or invoked `dns-filter`.

## What "clean" means now

After containment, the only definition of clean I trusted was the one I could verify.

The image got rebuilt from a known-good source, signed, and re-published. The host had `docker rmi` run against the poisoned image, which removed the layer from `/var/lib/docker/overlay2/`, which I confirmed by re-running the same forensic walk and getting nothing back. The running container was destroyed and recreated from the new image.

Validation was the same forensic sweep that found the miner originally:

- Run a `find /var/lib/docker/overlay2 -name 'dns-filter'` against the host (catches the specific binary; useful as a quick check, not durable since the next attacker will use a different name).
- Compare every layer's `diff/opt/flink/` listing against the new clean image's expected contents.
- SHA-256 every file in every diff directory and compare against an allow-list derived from the rebuilt image. This is the durable check.
- Pull the new image's digest from the registry and compare against the on-disk digest record after the next deploy.

A negative result on all four is the validation. The third one, the per-file SHA-256 sweep, is the one that would have caught a renamed variant of the same binary.

## What I will do differently

`ps` and `ss` are the wrong starting point for a containerized workload. They sample the running processes only and miss the persistence layer entirely. The forensic scope for a containerized IR has to include the image layers, the diff directories, the upperdir, and the registry digest record. Anything else and you are seeing only what the attacker wants visible at the moment you happen to look.

A `find /var/lib/docker/overlay2 -type f -newer <T>` is a five-second query and it would have caught this in the first pass. That command is going into the runbook, alongside the bandit-hardening checklist I wrote up recently for a different threat model in [Bandit-Clean Pwnagotchi Plugins]({filename}pwnagotchi-plugin-bandit-hardening.md). That post was about an imagined attacker with one foothold. This one was a real one with the same foothold and a much bigger blast radius.

The other thing I am changing is the order of the GuardDuty review. I read the AttackSequence finding well after the per-signal findings, because I was sweeping them in chronological order and AttackSequence was the most recent. The next time, the correlation finding gets read first. It is the cheapest path to the highest-confidence signal in the inbox, and it would have handed me the binary path before I started believing the host was clean.

There is a story to write about the other half of this incident, which is what happened on my analyst laptop while I was investigating the host. Falcon fired a true-positive on me partway through the work, because I `curl`'d the attacker's dropper into `/tmp` for hash analysis and that traffic looks identical to a real T1105 ingress tool transfer. That post is in the queue. The lesson there is that authorized analyst activity creates real EDR alerts and they need real attribution.

The container starts looking clean exactly when you stop looking carefully.
