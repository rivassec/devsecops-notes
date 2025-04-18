Title: Taming the OOM Killer: Process Prioritization for Memory-Constrained Linux Systems
Date: 2025-04-18
Tags: linux, oomkiller, memory, system-administration, devsecops, process-management, hardening
Category: DevSecOps
Slug: oom-killer-process-prioritization-revised
Author: Oliver Rivas
Summary: A practical and security-aware guide to defending critical processes from the Linux Out of Memory Killer by adjusting oom_score_adj dynamically at runtime.

In resource-constrained environments — especially virtual private servers, CI agents, and container hosts — the Linux kernel's **Out of Memory Killer (OOM Killer)** is a last-resort defense mechanism. When memory is exhausted, it begins terminating processes to keep the system alive.

The OOM Killer uses heuristics (like memory usage and the `oom_score_adj` value) to select processes it deems less essential. But you don’t have to leave that critical decision entirely to the kernel's default logic.

---

## 📉 The Incident

Years ago, I had to recover a VPS via remote console. A quick dive into `/var/log/messages` showed that the OOM Killer had struck, terminating critical services. The culprit? A perfect storm:

- Web crawlers (Google, Yahoo, Yandex) simultaneously indexing multiple sites
- A torrent tracker and download script both running
- IRC flood attempts while `irssi` was connected

This combination overwhelmed system memory. Without process priority tuning, the OOM Killer started targeting processes based on its heuristics, which felt indiscriminate from an operational view as it even took down `sshd`.

---

## ⚙️ The Mitigation Strategy

You can significantly influence OOM Killer decisions using the `/proc/<pid>/oom_score_adj` setting for a process. This value ranges from -1000 to +1000. The kernel uses this score, combined with memory usage, to decide kill priority; a lower score makes the process less likely to be chosen relative to others.

- A value of `-1000` effectively disables OOM killing for that process.
- A value of `+1000` makes it a highly preferred target.
- `0` is the default.

Here’s a script that reads preferences from a config file and adjusts running process scores accordingly.

### `/etc/oom_candidates.conf`

```conf
# Format: <process_name> <oom_score_adj_value>
# Higher = more likely to be killed. Negative = more protected.
# Critical Services (Protect Strongly)
sshd -1000
mysqld -500
portsentry -200

# Important Services (Protect Moderately)
apache2 100

# Less Critical Interactive/Background (Allow Killing)
screen 300
irssi 400
```

### `oom_adjuster.sh`

```bash
#!/bin/bash
CONFIG="/etc/oom_candidates.conf"

if [[ ! -f "$CONFIG" ]]; then
  echo "Error: Config file $CONFIG not found." >&2
  exit 1
fi

while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
  read -r process score <<< "$line"

  if [[ -z "$process" || -z "$score" ]]; then
    echo "Warning: Skipping invalid line: $line" >&2
    continue
  fi

  pids=$(pgrep -x "$process")
  if [[ -z "$pids" ]]; then
    continue
  fi

  echo "Adjusting OOM score for $process (PIDs: $pids) to $score"
  for pid in $pids; do
    if [[ -w "/proc/$pid/oom_score_adj" ]]; then
      echo "$score" > "/proc/$pid/oom_score_adj" 2>/dev/null
      if [[ $? -ne 0 ]]; then
         echo "Warning: Failed to set score for $process (PID: $pid)" >&2
      fi
    else
       echo "Warning: Cannot write to oom_score_adj for $process (PID: $pid)" >&2
    fi
  done
done < "$CONFIG"

echo "OOM score adjustment complete."
```

---

## 🧩 Running the Script

You can run this periodically via cron or on boot with systemd. For example:

### `/etc/systemd/system/oom-adjuster.service`

```ini
[Unit]
Description=Adjust OOM Scores from config file
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/oom_adjuster.sh

[Install]
WantedBy=multi-user.target
```

Then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now oom-adjuster.service
```

---

## 🔐 Security Considerations

From a DevSecOps perspective, OOM prioritization is not just about uptime — it’s a security hardening technique:

- **SSHD protection** prevents lockouts during memory exhaustion.
- **Preserving portsentry or IDS processes** ensures defense mechanisms remain active.
- **Avoiding the kill of logging/monitoring agents** helps retain forensic data post-incident.
- **Minimizing risk of service flapping** reduces noisy alerts and potential abuse vectors during DoS scenarios.

Misconfigured systems where critical daemons (like `iptables`, `auditd`, `sshd`, or VPN tunnels) are killed first expose themselves to avoidable downtime and security gaps.

---

## ✅ Modern Use Cases

- **Kubernetes nodes**: Influence OOM behavior via Quality of Service (QoS) classes (set by defining resource requests/limits in pod specs), or apply node-level tuning using methods like the script above for critical node components (e.g., kubelet, container runtime).
- **CI/CD runners**: Protect build agents or essential runner services from being killed during resource-intensive test suites or concurrent builds.
- **Shared hosting / VPS**: Prioritize core services (web server, database, SSH) over potentially less critical user processes or background tasks.

---

## 🔚 Conclusion

The OOM Killer is an essential part of the Linux kernel, but leaving process termination order purely to default heuristics can be risky in production. By strategically assigning `oom_score_adj` values based on business continuity and security priorities, you can significantly reduce recovery time and harden your systems against memory pressure scenarios.

**How does your team manage OOM Killer behavior in critical environments? Share your strategies!**

*Originally inspired by a real-world VPS recovery and refreshed for the modern DevSecOps landscape.*
