Title: TLS Has Three Jobs. Forget the Rest.
Date: 2026-06-04
Modified: 2026-06-04
Category: DevSecOps
Tags: tls, cryptography, security, infrastructure, pki, mtls, operations
Slug: tls-three-jobs
Author: RivasSec
Summary: TLS gets easier when you stop walking the handshake step by step and start naming what it is for. It does three jobs. Once those are anchored, the protocol stops being a memorization problem and becomes a design problem.
Cover: images/covers/tls-three-jobs.png

[TOC]

TLS gets easier when you stop walking the handshake step by step and start naming what it is for. There are too many round trips, too many cipher suites, too many extensions, and the version in your head is rarely the one in front of you.

Every TLS handshake, in every version, is doing three jobs at the same time:

1. **Key agreement.** Two parties who have never spoken derive the same secret over a public network without sending it.
2. **Server authentication.** The server proves it is the entity the client meant to talk to.
3. **Session-key derivation.** Both sides turn that shared secret into the symmetric keys that encrypt the actual application data.

If you can hold those three in your head, the rest of the protocol is an implementation detail. The differences between TLS 1.2 and TLS 1.3 collapse into "which mechanisms got removed for being unsafe." The cipher suite alphabet soup collapses into "which algorithm fills which job."

## How the three jobs map to the wire

In TLS 1.3, the handshake takes one round trip:

- **ClientHello** — supported ciphers, an ECDHE public key share, the server name (SNI).
- **ServerHello** — chosen cipher, server's ECDHE public key share, server certificate, signature over the handshake transcript. From this point forward the handshake is encrypted.
- **Client side** — verifies the certificate chain, uses its private ECDHE key plus the server's public ECDHE key to compute the shared secret. Both sides feed that secret through HKDF to derive symmetric keys.
- **Finished** messages on both sides confirm nothing was tampered with mid-handshake. Application data starts.

Three jobs, one round trip. Key agreement is ECDHE. Server authentication is the certificate plus the signature. Session-key derivation is HKDF. The version that does this in two round trips with optional unsafe modes is TLS 1.2.

## What got removed in TLS 1.3 and why

The honest one-line difference is "TLS 1.3 deleted the parts that kept getting people compromised."

- **RSA key exchange is gone.** In TLS 1.2 a server could choose to encrypt the pre-master secret to its own RSA public key. If that private key ever leaked, every recorded session that used it was retroactively decryptable. TLS 1.3 only allows ephemeral Diffie-Hellman, which gives you forward secrecy by default.
- **CBC mode ciphers are gone.** BEAST, Lucky13, and the rest of the padding-oracle family lived here. TLS 1.3 only allows AEAD ciphers — AES-GCM and ChaCha20-Poly1305.
- **MAC-then-encrypt is gone.** AEAD modes do authentication and encryption in one pass.
- **Compression is gone.** CRIME exploited it.
- **Renegotiation is gone.** It was a footgun for years.

The cipher suite list in TLS 1.3 has five entries. In TLS 1.2 it has hundreds. That is the whole story.

## The certificate chain is where most outages live

Server authentication is done by certificate, but the client does not trust the server's certificate directly. It trusts a chain:

- The server's leaf certificate, signed by an intermediate CA.
- The intermediate CA's certificate, signed by a root CA.
- The root CA's certificate, sitting in the operating system or browser trust store.

Validation, in order, is roughly:

1. Hostname matches the certificate's Subject Alternative Name.
2. Certificate is within its validity window.
3. Signature chain reaches a trusted root.
4. Certificate has not been revoked (CRL or OCSP).
5. Key usage permits server authentication.

Most production TLS incidents are not protocol bugs. Every TLS outage I have debugged falls into one of four buckets: an expired intermediate, a leaf certificate rotated without rolling the clients that pinned it, an OCSP responder timing out under load, or a trust store that drifted after an AMI bump. The protocol is fine. The operational surface around it is where the pages come from.

## What I actually type when something is broken

Most TLS triage is two or three commands.

```
# what is the server actually presenting, including chain
openssl s_client -connect host:443 -servername host -showcerts </dev/null

# what does this leaf actually say
openssl x509 -in cert.pem -noout -text | grep -E 'Not After|Subject:|Issuer:|DNS:'

# does it validate against the system trust store
curl -vI https://host 2>&1 | grep -E 'expire|subject|issuer|verify'

# is the chain Mozilla-trusted, or am I missing an intermediate
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt -untrusted intermediate.pem leaf.pem
```

If the answer is "expired", you are done. If the answer is "no issuer found", an intermediate is missing from what the server is sending. If the answer is "hostname mismatch", the SAN does not include what the client asked for. Those three account for most of the calls.

## mTLS is the same thing in both directions

Mutual TLS just adds a second authentication step: the server requires the client to present a certificate, and the server validates that certificate against an internal CA. Same primitives, same chain logic, same revocation question — just now the client is also proving who it is.

It matters because in a serverless or microservices fabric, mTLS is the cleanest replacement for "shared secrets in environment variables." Service identity becomes a certificate issued by an internal CA, rotated automatically by something like cert-manager or AWS Private CA. The handshake is doing the same three jobs; you just stopped trusting the network and started trusting the certificate. The "refuse the dangerous default unless the caller asks for it explicitly" pattern that makes that workable on the IAM side is the subject of [IAM Roles That Fail Loud]({filename}iam-safe-defaults-fail-loud.md).

## Where the operational work actually lives

In a real design review, the handshake recitation is the wrong shape anyway. The interesting questions are operational:

- **Certificate lifecycle.** Auto-rotation with ACM for AWS-fronted services, cert-manager for Kubernetes, internal CA for service-to-service mTLS. Most TLS outages are expiry-driven, and the way out is the same paved-road pattern that fixes everything else: ship the rotation as a default, not as a checklist. I wrote about that program shape in [Adoption Is a Security Control]({filename}paved-road-adoption-as-control.md).
- **Termination boundary.** Where does TLS terminate, where does it re-originate, what is in cleartext between those points. ALB-terminated traffic to an HTTP backend is a different threat model than end-to-end mTLS.
- **Cipher policy.** TLS 1.2 minimum, AEAD-only, no RSA key exchange, no legacy versions. The defaults from a serious load balancer are usually fine; the failure mode is leaving 1.0 or 1.1 on for "compatibility" and forgetting.
- **Trust store hygiene.** Pinning, revocation checking, intermediate cert distribution. The boring half of the protocol is where the real attacks land.

The handshake is well understood. The real risk lives in mis-configured trust stores, expired intermediates, and downgrade paths kept around for legacy clients that nobody actually has anymore.

Three jobs, in parallel, in every version: key agreement, server authentication, session-key derivation. Once you see the protocol that way, the handshake stops being a sequence to memorize and becomes the smallest, most boring part of running TLS in production.
