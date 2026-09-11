Title: Finding the Cryptominer Hiding in a Docker overlay2 Layer
Date: 2026-09-11 09:00
Modified: 2026-09-11 09:00
Author: Oliver Rivas
Category: DevSecOps
Tags: incident-response, devsecops, docker, forensics
Series: Anatomy of a Container Incident
Slug: cryptominer-in-the-docker-layer
Og_image: images/og/cryptominer-in-the-docker-layer.png
Summary: A runtime detector flagged mining but ps and ss came back clean. The miner lived in the image's overlay2 diff layer, relaunched on every container restart.
Cover: images/covers/cryptominer-in-the-docker-layer.png

[TOC]

During an incident-response engagement, I worked through a case where the on-disk picture and the runtime picture were saying different things. The cloud provider's threat-detection service fired several correlated findings on a containerized workload: two cryptomining DNS detections (one against the host, one against a container running on it), one resolver-level finding for the same lookups, and a correlation finding that stitched them all into a single critical-severity event. The destination was a public Monero mining pool. The instance was running a JVM-based service.

I opened an SSM session onto the host, ran `ps -ef` inside the container, ran `ss -tunap`, and found nothing. No miner process. No outbound connection to the pool. No CPU pressure. The Java heap looked normal. The application was happily doing what the application was supposed to be doing.

For a while I was sure I was looking at a false-positive.

I was not.

The miner was on disk, in one of the image's [overlay2](https://docs.docker.com/engine/storage/drivers/overlayfs-driver/) layers. The container's filesystem could see it through the union mount, but the binary was not in the process space at the moment I checked, which is what `ps` reports. The persistence lived in a layer that survives `docker compose down -v`, which meant any container created from the affected image would inherit the file if the image itself was the source of the persistence. This post is about the sweep that found it, what I now know to look at on the next one, and what I am still not sure about.

## The shape of the alert

A modern cloud-detector IR loop has two tiers. There are the per-signal findings, which fire on a single observation: a DNS query to a known mining pool, an SSH brute-force attempt, a port scan against a sensitive port. In my experience, most of them are individually low-confidence and will resolve as false-positive once a human looks.

Then there are the correlation findings. AWS GuardDuty calls these [`AttackSequence` findings](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty-extended-threat-detection.html); other clouds and EDRs have analogues. The defining property is that they do not fire on a single signal. They fire when the detector has stitched several signals into a coherent story: a brute-force from a known-bad IP, then a port probe from a different known-bad IP, then a process inside a container talking to a mining pool, all on the same instance, in the same window. The finding hands you the timeline pre-assembled. That correlation tier is where the noise reduction actually happens: many weak signals in, one high-confidence story out.

Per-signal findings can be wrong. Correlation findings can be wrong too, but in my experience they earn priority because they pre-stitch the timeline and tend to carry the highest-confidence detail in the inbox.

In this case the correlation finding listed the file path on disk:

```
/opt/<app>/.<hidden_dir>/lib/<obfuscated_subdir>/<binary>
```

That string was in the JSON - not a heuristic or a prediction, an actual on-disk path. The runtime sensor had observed the binary executing and recorded its on-disk location.

That is when I went looking on the host.

## The path that mattered

The container view is not the host view. Inside the running container, the binary path resolved to whatever the overlayfs union mount made visible at that moment. From the host, the same content lives in several overlay2 directories depending on what you are asking about. The four roles to know:

| Directory | Role | Survives container exit? |
|---|---|---|
| `lowerdir` (`diff` on each lower layer) | Read-only contribution from a build-time image layer | Yes; removed only by image removal (`docker rmi` / image prune) |
| `merged` | Live union view the container sees as `/` | No, unmounted when container stops |
| `upperdir` | Writable layer the container modifies at runtime | Yes (until container is removed) |
| `workdir` | Overlay's internal scratch space | Directory persists until container removal; contents are transient scratch, nothing forensically durable |

Two of these matter for the rest of this story:

- the image's diff directory (where the binary actually lived)
- the merged view (what the container saw)

The first one is the image's diff directory:

```
/var/lib/docker/overlay2/<image-layer-id>/diff/opt/<app>/.<hidden_dir>/lib/<obfuscated_subdir>/<binary>
```

The second one is the merged view, which is what the running container actually sees. Note the different directory ID: the merged mount lives under the container's own layer directory, not under the poisoned lower layer's:

```
/var/lib/docker/overlay2/<container-layer-id>/merged/opt/<app>/.<hidden_dir>/lib/<obfuscated_subdir>/<binary>
```

These two paths are related but not equivalent, and the difference is what the rest of the investigation turns on.

The lifecycle is the part the table cannot carry. A binary `COPY`'d into an image at build time lives in some layer's `diff` directory from the moment of `docker pull`, and `docker rm` of the container does not touch it - the files belong to the image. `merged` is the opposite: it is the union view the container sees as its filesystem root, it exists only while the container runs, and unmounting it leaves every underlying `diff` directory in place.

I also checked `upperdir` and `workdir`. The malicious binary was in neither. It was in a lower layer's `diff` directory, the read-only foundation that came down with the image pull.

To make sure I had the layer role right, I cross-referenced against `docker inspect <container>`. The `GraphDriver.Data.LowerDir` chain on the running container included this directory in its read-only stack, which is what marks it as an image-side lower layer rather than the container's writable upper. `docker history` told me the image had `COPY` steps in its build (which is unsurprising for any non-trivial image) but `docker history` shows the instruction, not the per-file provenance, so I am not claiming it identified the specific binary. The shape of the evidence is "this layer is in the LowerDir chain, the LowerDir chain is read-only, the running container's writable space is empty for this path." That is enough to place the file in an image layer.

That distinction matters. A miner in the writable upperdir would be a runtime drop, written into the container after it started, possibly by a process inside it. A miner in an image layer means the layer itself is the persistence mechanism. If that layer originated from the image (rather than from on-disk tampering, which I cover next), every container created from this image inherits the file at birth.

## What the binary did

The pattern I inferred (and want to flag as inferred, since I never finished reconstructing the execution chain) is that the binary ran shortly after container start, fired one DNS query to the pool, tried to start mining, and died before steady state. The application's JVM was using almost all the cgroup memory and the miner could not get a foothold. By the time I looked, the process was not on the system anymore. The runtime sensor logged the execution and the DNS query each cycle; the per-execution timestamps and process ancestry would have helped me pin down the precise launch path, but I did not go back for them before the rebuild closed the investigation out. Whether they were still sitting in the detector's finding records or gone with the host, the window that closed was mine.

This is why `ps` was empty.

The binary was not self-contained, either: it referenced a dropper script on a content-delivery URL and a second-stage payload on a paste service. Retrieving those artifacts for hashing set off its own incident - a story I am writing up separately.

The pattern repeated on every restart. There had been an unusual amount of container churn for an unrelated stability issue. Each restart re-mounted the poisoned layer, and the sensor logged the execution and the DNS query each cycle; by the inference above, the miner came up briefly, lost the resource fight, and died. The host-level `ps` view, sampled later by a human, missed it every time.

I calculated and tracked the binary's SHA-256 during analysis (it was around 9.8 MB, owned by the application's runtime user). I am not publishing the hash here; it is a real IOC from a real incident and serves no educational purpose in the post.

One caution on timestamps: file mtimes inside an image layer are weak forensic evidence - tar archives can preserve build-host timestamps, `COPY` carries them across, and an attacker with write access can `touch` whatever they want.

The path on disk used a leading dot for the parent directory so a casual `ls` of the parent did not show it. The binary's name was a plausible-sounding match for the kinds of helpers the application legitimately ships. The disguise was decent, not great: exactly good enough to survive a reviewer glancing at a file listing.

## Was the image poisoned at build time, or on disk?

This is where the post stops being a clean story.

Two explanations remained plausible. The first is a supply-chain compromise of the registry: OCI digests are content-addressed and cannot be mutated in place, but the *tag* a deployment tracks maps to a digest, and that mapping can be moved by anyone with push access to the repository. A fresh pull after a tag rewrite would surface a malicious layer without anything happening on the host. The second is on-disk tampering: a process on the host with root access - or `docker`-group access, which is root-equivalent via the socket - writing into the local layer storage.

A digest comparison between the host's recorded image digest and the registry's currently-advertised digest for the tag will tell you the tag is *currently* mapped to the digest the host has. It does not tell you whether the tag was *ever* pointed at a different digest in the meantime. The cleanest defense against this whole class of question is to deploy by immutable identifier (`repo@sha256:<digest>`) in your manifests, not by tag. The deployment record itself becomes the audit trail and a tag rewrite cannot retroactively change what got pulled. Registry-side tag immutability (ECR immutable tags, Harbor's immutable tag rules) is the complementary control on the other end: it prevents the retarget outright and leaves a registry audit event when someone tries. A naive `cp` into a diff directory leaves the layer content out of sync with the metadata Docker keeps in `layerdb` (and the image configs in `imagedb`); a defender can check for that mismatch, and a thorough tamperer would have to forge both, which is why clean on-disk tampering is hard to rule out.

Because containment took priority over historical reconstruction, attribution remained unresolved, and I am writing it that way on purpose. Most incident write-ups jump to attribution because attribution makes the story feel done. The middle of the story is "find the malware on disk." The end is "tell people how to find it." Attribution sits outside this scope.

The execution-chain gap I flagged earlier is the second thing I did not close before rebuild. Candidates for what launched the binary included the image's `ENTRYPOINT`, the application's bootstrap shell scripts, an `LD_PRELOAD` in the image, a startup hook in the container's init system, or a sidecar I had not noticed. With more time, the first thing I would walk is `docker inspect <image>` for `Entrypoint` and `Cmd`, then every shell script those reference, looking for the line that invokes the binary.

## What "clean" means now

After containment, the only definition of clean I trusted was the one I could verify.

The image got rebuilt from a known-good source, signed, and re-published. Signing pays off only where verification is enforced at pull or deploy; unverified, it is an audit trail, not a control. The host had `docker rmi` run against the poisoned image, which removed the layer from `/var/lib/docker/overlay2/`. Note that `rmi` only drops a layer once no other image, tag, or stopped container still references it, which is why the confirming sweep is part of the sequence rather than optional: I re-ran the same forensic walk and got nothing back. The running container was destroyed and recreated from the new image, and the host itself was rebuilt. That last step matters more than it sounds: while the on-disk-tampering hypothesis stays open, a resident root-level actor survives any amount of image hygiene, so the sweep below validates a snapshot, not an eviction. Treat an unruled-out tampering hypothesis as a compromised host - replace it, and rotate every credential reachable from it.

Validation was the same forensic sweep that found the miner originally:

- Run a `find /var/lib/docker/overlay2 -name '<binary-name>'` against the host. Useful as a quick name-based check; not durable since the next attacker will use a different name.
- Generate a file manifest from the rebuilt image and compare layer contents on the host against that expected manifest. Investigate any unexpected file, not just an exact name match.
- Pull the new image's digest from the registry and compare against the on-disk digest record after the next deploy.

A clean result on all three is the validation. The manifest comparison is the durable check; it catches a renamed variant of the same binary or anything else the attacker might add to the layer that the image's build does not produce. The triad has a scope, though: it validates against tag retargeting and on-disk tampering, and it assumes the build inputs are trusted. Verifying the base image digest and the build pipeline is the separate check that closes the build-side vector.

## What I will do differently

`ps` and `ss` are reasonable first-pass triage, but they are not evidence that a containerized workload is clean. They sample runtime state at one instant and say nothing about dormant persistence in the image layers or the writable layer. Running them was not the mistake; the mistake was nearly letting a clean runtime observation answer a filesystem question. The forensic scope for a containerized IR has to include the image layers, the diff directories, the upperdir, and the registry digest record. Anything else and you are seeing only what the attacker wants visible at the moment you happen to look. One scoping check before any of it: confirm the storage driver with `docker info`. Docker Engine 29.0+ defaults fresh installs to the containerd image store (upgraded hosts keep their existing driver), and there layer content lives under containerd's snapshotter paths instead of `/var/lib/docker/overlay2` - so an empty overlay2 sweep on such a host is not a clean result, it means you looked in the wrong place.

The general rule the incident taught me: a clean result is only meaningful within the scope of the question you asked. `ps` can say the miner is not running right now. An upperdir sweep can say it was not persisted there. A manifest comparison can say the filesystem matches the artifact I expected, and provenance can say that artifact came through a build I trust. None of these answers substitutes for another, and they run from weakest to strongest: a filename search is the cheapest check and the easiest to defeat, build provenance the hardest. The failure mode is letting a strong answer to a weak question close the incident.

A `find /var/lib/docker/overlay2 -type f -newermt '<incident start>'` is a five-second query, and it is the first-pass catch for runtime drops written into `upperdir` - a different case than this incident. The catch: if the binary was baked into the image at build time, its mtime inside the layer can reflect the image-build date, which could be weeks or months earlier than the incident. A recency filter would miss that. The manifest comparison from the previous section is what closes the gap.

The other thing I am changing is the order in which I read cloud-detector findings. I read the correlation finding well after the per-signal findings, because I was sweeping them in chronological order and the correlation was the most recent. The next time, the correlation gets read first. It is the cheapest path to the highest-confidence signal in the inbox, and it would have handed me the binary path before I started believing the host was clean.

The next incident I investigate will start with the image layers. The container starts looking clean exactly when you stop looking carefully.

## Related reading

- [Bandit-Clean Pwnagotchi Plugins]({filename}pwnagotchi-plugin-bandit-hardening.md): different threat model, same habit: trust resolved full paths and verified content, never what a file's name claims it is.
