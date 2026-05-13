Title: Hardening Kubernetes Deployments
Date: 2025-04-19
Category: Kubernetes Security
Tags: kubernetes, hardening, pod-security-standards
Slug: hardening-k8s
Author: RivasSec
Summary: Pod-level Kubernetes guardrails aligned with the Pod Security Standards Restricted profile: non-root, no caps, read-only FS, NetworkPolicies, SA hardening.

Securing Kubernetes workloads isn't just about scanning images or tweaking RBAC, it's about enforcing the right guardrails at the pod level to minimize risk by default. This post shares field-tested strategies aligned with the Pod Security Standards (Restricted profile) to help you build safer, production-grade deployments.

## Key Practices for Hardening Kubernetes Deployments

### 1. Run Containers as Non-Root

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 3000
```

This enforces that containers don’t run as UID 0, reducing the blast radius of any compromise.

---

### 2. Drop All Linux Capabilities

```yaml
securityContext:
  capabilities:
    drop:
      - ALL
    add:
      - NET_BIND_SERVICE  # Only if your app needs it (e.g., for ports <1024)
```

Drop all capabilities by default, then add only what you need.

---

### 3. Disable Privilege Escalation

```yaml
securityContext:
  allowPrivilegeEscalation: false
```

This prevents processes inside the container from gaining additional privileges, even if compromised.

---

### 4. Use Read-Only Filesystem

```yaml
securityContext:
  readOnlyRootFilesystem: true
```

This blocks attackers from writing malicious files or installing tools inside the container.

---

### 5. Avoid Host Access

```yaml
hostNetwork: false
hostPID: false
hostIPC: false
```

Avoid `hostPath` volumes unless absolutely required. These settings ensure your workloads remain isolated from the host.

---

### 6. Use Trusted Images and Scan Them

Use minimal base images (Alpine, Distroless) and trusted registries. Always scan them:

```bash
trivy image your-registry/app:tag
```

This helps catch known CVEs before deployment.

---

### 7. Handle Secrets via Volumes (Not Env Vars)

```yaml
volumes:
  - name: secret-volume
    secret:
      secretName: my-secret

containers:
  - name: myapp
    volumeMounts:
      - name: secret-volume
        mountPath: "/etc/secret"
        readOnly: true
```

Mounting secrets as volumes avoids accidental exposure via logs or `/proc`.

---

### 8. Restrict Network Traffic with NetworkPolicies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
spec:
  podSelector: {}
  policyTypes:
    - Ingress
```

Start with a default-deny policy per namespace, then explicitly allow only the traffic your services need. Without NetworkPolicies, any pod can communicate with any other pod in the cluster.

---

### 9. Harden ServiceAccount Usage

```yaml
automountServiceAccountToken: false
```

Disable automatic token mounting for pods that don’t need API server access. Create dedicated ServiceAccounts with minimal RBAC bindings rather than relying on the `default` account, which often accumulates unnecessary permissions.

---

## Final Thoughts

Security isn’t just about tools, it’s about secure defaults. These practices help harden your Kubernetes workloads using the Restricted Pod Security Standard and reduce risks across the board.

If you’re managing production clusters or sensitive environments, these changes are low-hanging fruit with a high return on security posture. The same "safe by default" mindset applied to AWS IAM is the subject of [IAM Roles That Fail Loud]({filename}iam-safe-defaults-fail-loud.md); for the node side of memory pressure, see [Taming the OOM Killer]({filename}oom-killer-process-prioritization.md).
