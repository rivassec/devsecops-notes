Title: About
Slug: about
Author: RivasSec
Summary: Security engineer profile - cloud-native infrastructure security, Kubernetes and AWS IAM hardening, compliance automation.

## Staff Security Engineer - Cloud & Platform Security

I build and ship security controls in public: an AWS IAM blast-radius
analyzer with a live tool, a Pulumi IAM library with safe defaults, and
a threat-model addendum for the case where the operator is the adversary.

Most of my day-job security work happens in private repositories, so this
profile shows the side of it I can build in public.

---

### Projects

* [`secure-iam-lint`](https://github.com/rivassec/secure-iam-lint) - Client-side AWS IAM policy blast-radius analyzer (fail-closed, zero-backend); powers the live tool at [rivassec.com/tools/iam-blast-radius](https://rivassec.com/tools/iam-blast-radius/). [Testing an IAM Analyzer Against Its Own Claims](https://rivassec.com/testing-an-iam-analyzer-against-its-own-claims.html)
* [`iam-safe-defaults`](https://github.com/rivassec/iam-safe-defaults) - Pulumi component library for AWS IAM with safe defaults that fail loud: mandatory permissions boundary, no wildcard trust, every opt-out explicit. [IAM Roles That Fail Loud](https://rivassec.com/iam-safe-defaults-fail-loud.html)
* [`weaponization-threat-model`](https://github.com/rivassec/weaponization-threat-model) - One-page addendum to STRIDE/LINDDUN/PASTA for modeling the legitimate operator as the adversary. Applied in [When Telemetry Turns Predatory](https://rivassec.com/telemetry-turns-predatory.html)
* [`devsecops-notes`](https://github.com/rivassec/devsecops-notes) - Source for [rivassec.com](https://rivassec.com): Pelican with link-check, accessibility (pa11y), and gitleaks CI.
* Smaller and archival: [`cf-token-links`](https://github.com/rivassec/cf-token-links) (token-scoped redirects), [`elasticsearch-tools`](https://github.com/rivassec/elasticsearch-tools) (least-privilege snapshot verification), [`efi-bruteforce`](https://github.com/rivassec/efi-bruteforce) (2013 Teensy EFI research, featured on Hackaday).

---

### Writing - [rivassec.com](https://rivassec.com)

Start here: [Testing an IAM Analyzer Against Its Own Claims](https://rivassec.com/testing-an-iam-analyzer-against-its-own-claims.html). Latest:

<!-- BLOG-POST-LIST:START -->
- [Every Alert Is Your Alert: When IR Tooling Trips Your Own EDR](https://rivassec.com/every-alert-is-your-alert.html)
- [Finding the Cryptominer Hiding in a Docker overlay2 Layer](https://rivassec.com/cryptominer-in-the-docker-layer.html)
- [When Telemetry Turns Predatory: A DevSecOps Look at Digital Repression in Venezuela](https://rivassec.com/telemetry-turns-predatory.html)
<!-- BLOG-POST-LIST:END -->

---

> Controls that fail closed.
