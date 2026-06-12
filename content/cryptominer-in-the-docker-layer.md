Title: How I Learned to Investigate Docker Image Layers During Incident Response
Date: 2026-06-24
Modified: 2026-06-24
Author: RivasSec
Category: DevSecOps
Tags: incident-response, docker, overlay2, cryptominer, guardduty, aws, forensics
Slug: cryptominer-in-the-docker-layer
Summary: A runtime detector said the host was mining. `ps` and `ss` came back clean. The miner was hiding one layer lower, baked into the image's overlay2 diff directory and re-dropped on every container restart. A walk through the IR sweep that almost called it a false-positive.
Cover: images/covers/cryptominer-in-the-docker-layer.png
Status: draft

[TOC]

During a recent incident-response engagement, I worked through a case where the on-disk picture and the runtime picture were saying different things. The cloud provider's threat-detection service fired several correlated findings on a containerized workload: two cryptomining DNS detections (one against the host, one against a container running on it), one resolver-level finding for the same lookups, and a correlation finding that stitched them all into a single critical-severity event. The destination was a public Monero mining pool. The instance was running a Java-based data-processing application.

I opened an SSM session onto the host, ran `ps -ef` inside the container, ran `ss -tunap`, and found nothing. No miner process. No outbound connection to the pool. No CPU pressure. The Java heap looked normal. The application was happily doing what the application was supposed to be doing.

For a while I was sure I was looking at a false-positive.

I was not.

The miner was on disk, in one of the image's overlay2 layers. The container's filesystem could see it through the union mount, but the binary was not in the process space at the moment I checked, which is what `ps` reports. The persistence lived in a layer that survives `docker compose down -v`, which meant any container created from the affected image would inherit the file if the image itself was the source of the persistence. This post is about the sweep that found it, what I now know to look at on the next one, and what I am still not sure about.

## The shape of the alert

A modern cloud-detector IR loop has two tiers. There are the per-signal findings, which fire on a single observation: a DNS query to a known mining pool, an SSH brute-force attempt, a port scan against a sensitive port. They are designed for noise reduction. Most of them are individually low-confidence and will resolve as false-positive once a human looks.

Then there are the correlation findings. AWS GuardDuty calls these `AttackSequence` findings; other clouds and EDRs have analogues. The defining property is that they do not fire on a single signal. They fire when the detector has stitched several signals into a coherent story: a brute-force from a known-bad IP, then a port probe from a different known-bad IP, then a process inside a container talking to a mining pool, all on the same instance, in the same window. The finding hands you the timeline pre-assembled.

Per-signal findings can be wrong. Correlation findings can be wrong too, but in my experience they earn priority because they pre-stitch the timeline and tend to carry the highest-confidence detail in the inbox. The lesson I keep relearning is to read them first, especially before declaring per-signal findings false-positive.

In this case the correlation finding listed the file path on disk:

```
/opt/<app>/.<hidden_dir>/lib/<obfuscated_subdir>/<binary>
```

That string was in the JSON. Not a heuristic, not a prediction, a path. The runtime sensor had observed the binary executing and recorded its on-disk location.

That is when I went looking on the host.

## The path that mattered

The container view is not the host view. Inside the running container, the binary path resolved to whatever the overlayfs union mount made visible at that moment. From the host, the same content lives in several overlay2 directories depending on what you are asking about. The four roles to know:

| Directory | Role | Survives container exit? |
|---|---|---|
| `lowerdir` (`diff` on each lower layer) | Read-only contribution from a build-time image layer | Yes; only `docker rmi` removes it |
| `merged` | Live union view the container sees as `/` | No, unmounted when container stops |
| `upperdir` | Writable layer the container modifies at runtime | Yes (until container is removed) |
| `workdir` | Overlay's internal scratch space | No |

Two of these matter for the rest of this story:

- the image's diff directory (where the binary actually lived)
- the merged view (what the container saw)

The first one is the image's diff directory:

```
/var/lib/docker/overlay2/<layer-id>/diff/opt/<app>/.<hidden_dir>/lib/<obfuscated_subdir>/<binary>
```

The second one is the merged view, which is what the running container actually sees:

```
/var/lib/docker/overlay2/<layer-id>/merged/opt/<app>/.<hidden_dir>/lib/<obfuscated_subdir>/<binary>
```

These two paths are related but not equivalent, and the difference is the entire post.

The `diff` directory is a layer's contribution to the union. If you wrote a Dockerfile and `COPY`'d a binary into the image at build time, that binary lives in some layer's `diff` directory forever. When you `docker pull` the image, those files arrive on disk. When you `docker rm` the container they stay there, attached to the image, not to any specific running container.

The `merged` directory is the union view of all layers stacked together. It is what the container sees as its filesystem root. When the container runs, processes inside it read from `merged`. When the container stops, `merged` is unmounted, but the underlying `diff` directories remain.

I also checked `upperdir` and `workdir`. The malicious binary was in neither. It was in a lower layer's `diff` directory, the read-only foundation that came down with the image pull.

To make sure I had the layer role right, I cross-referenced against `docker inspect <container>`. The `GraphDriver.Data.LowerDir` chain on the running container included this directory in its read-only stack, which is what marks it as a build-time image layer rather than the container's writable upper. `docker history` told me the image had `COPY` steps in its build (which is unsurprising for any non-trivial image) but `docker history` shows the instruction, not the per-file provenance, so I am not claiming it identified the specific binary. The shape of the evidence is "this layer is in the LowerDir chain, the LowerDir chain is read-only, the running container's writable space is empty for this path." That is enough to place the file in an image layer.

That distinction matters. A miner in the writable upperdir would be a runtime drop, written into the container after it started, possibly by a process inside it. A miner in an image layer means the image itself is the persistence mechanism. If that layer originated from the image (rather than from on-disk tampering, which I cover next), every container created from this image inherits the file at birth.

## What the binary did

The pattern I inferred (and want to flag as inferred, since I never finished reconstructing the execution chain) is that the binary ran shortly after container start, fired one DNS query to the pool, tried to start mining, and died before steady state. The application's JVM was using almost all the cgroup memory and the miner could not get a foothold. By the time I looked, the process was not on the system anymore. The runtime sensor logged the execution and the DNS query each cycle; the per-execution timestamps and process ancestry would have helped me pin down the precise launch path, but I did not extract them from the sensor's records before the host got rebuilt.

This is why `ps` was empty.

The pattern repeated on every restart. There had been an unusual amount of container churn for an unrelated stability issue. Each restart re-mounted the poisoned layer, the miner came up briefly, fired DNS, lost the resource fight, and died. The runtime sensor caught the DNS each time. The host-level `ps` view, sampled later by a human, missed it every time.

We calculated and tracked the binary's SHA-256 during analysis (it was around 9.8 MB, owned by the application's runtime user). I am not publishing the hash here; it is a real IOC from a real incident and serves no educational purpose in the post.

I will note here that file mtimes inside an image layer are weak forensic evidence: tar archives can preserve build-host timestamps, `COPY` carries them across, and an attacker with write access can `touch` whatever they want. I am treating mtime as a clue, not as proof of when the file arrived on the host.

The path on disk used a leading dot for the parent directory so a casual `ls` of the parent did not show it. The binary's name was a plausible-sounding match for the kinds of helpers the application legitimately ships. The disguise was decent. It was not great. It was exactly good enough to survive a reviewer glancing at a file listing.

## Was the image poisoned at build time, or on disk?

This is where the post stops being a clean story.

Two explanations remained plausible. The first is a supply-chain compromise of the registry: OCI digests are content-addressed and cannot be mutated in place, but the *tag* a deployment tracks maps to a digest, and that mapping can be moved by anyone with push access to the repository. A fresh pull after a tag rewrite would surface a malicious layer without anything happening on the host. The second is on-disk tampering: a process on the host with root or `docker`-group access modifying the local layer storage directly.

A digest comparison between the host's recorded image digest and the registry's currently-advertised digest for the tag will tell you the tag is *currently* mapped to the digest the host has. It does not tell you whether the tag was *ever* pointed at a different digest in the meantime. The cleanest defense against this whole class of question is to deploy by immutable identifier (`repo@sha256:<digest>`) in your manifests, not by tag. The deployment record itself becomes the audit trail and a tag rewrite cannot retroactively change what got pulled. On-disk tampering is also harder to disprove than a `cp`-style edit, because Docker stores layer metadata in `imagedb` and a thorough tamperer would update both.

Because containment took priority over historical reconstruction, attribution remained unresolved, and I am writing it that way on purpose. Most incident write-ups jump to attribution because attribution makes the story feel done. The middle of the story is "find the malware on disk." The end is "tell people how to find it." Attribution sits outside this scope.

There is a second gap I did not close before rebuild: the execution chain. I confirmed the binary executed and I confirmed it lived on disk in an image layer, but I did not finish reconstructing what launched it. Candidates included the image's `ENTRYPOINT`, the application's bootstrap shell scripts, an `LD_PRELOAD` in the image, a startup hook in the container's init system, or a sidecar I had not noticed. With more time, the first thing I would walk is `docker inspect <image>` for `Entrypoint` and `Cmd`, then every shell script those reference, looking for the line that invokes the binary.

## What "clean" means now

After containment, the only definition of clean I trusted was the one I could verify.

The image got rebuilt from a known-good source, signed, and re-published. The host had `docker rmi` run against the poisoned image, which removed the layer from `/var/lib/docker/overlay2/`, which I confirmed by re-running the same forensic walk and getting nothing back. The running container was destroyed and recreated from the new image.

Validation was the same forensic sweep that found the miner originally:

- Run a `find /var/lib/docker/overlay2 -name '<binary-name>'` against the host. Useful as a quick name-based check; not durable since the next attacker will use a different name.
- Generate a file manifest from the rebuilt image and compare layer contents on the host against that expected manifest. Investigate any unexpected file, not just an exact name match.
- Pull the new image's digest from the registry and compare against the on-disk digest record after the next deploy.

A clean result on all three is the validation. The manifest comparison is the durable check; it catches a renamed variant of the same binary or anything else the attacker might add to the layer that the image's build does not produce.

## What I will do differently

`ps` and `ss` are the wrong starting point for a containerized workload. They sample the running processes only and miss the persistence layer entirely. The forensic scope for a containerized IR has to include the image layers, the diff directories, the upperdir, and the registry digest record. Anything else and you are seeing only what the attacker wants visible at the moment you happen to look.

A `find /var/lib/docker/overlay2 -type f -newer <T>` is a five-second query and it would have caught this in the first pass for runtime drops written into `upperdir`. The catch: if the binary was baked into the image at build time, its mtime inside the layer can reflect the image-build date, which could be weeks or months earlier than the incident. `-newer` would miss that. The manifest comparison from the previous section is what closes the gap; for layers built today, it would have flagged a binary that does not appear in the build's expected contents regardless of the binary's mtime.

The other thing I am changing is the order in which I read cloud-detector findings. I read the correlation finding well after the per-signal findings, because I was sweeping them in chronological order and the correlation was the most recent. The next time, the correlation gets read first. It is the cheapest path to the highest-confidence signal in the inbox, and it would have handed me the binary path before I started believing the host was clean.

The next incident I investigate will start with the image layers. The container starts looking clean exactly when you stop looking carefully.

## Related reading

- [Bandit-Clean Pwnagotchi Plugins]({filename}pwnagotchi-plugin-bandit-hardening.md): different threat model, same lesson about how a binary's threat surface depends on where it lives, not what it claims to be.
