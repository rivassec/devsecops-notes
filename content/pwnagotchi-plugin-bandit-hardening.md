Title: Bandit-Clean Pwnagotchi Plugins: How `subprocess` Goes From Risk to Routine
Date: 2026-06-10
Modified: 2026-06-10
Category: DevSecOps
Tags: pwnagotchi, python, bandit, subprocess, security, supply-chain, hardening
Slug: pwnagotchi-plugin-bandit-hardening
Author: RivasSec
Summary: Pwnagotchi plugins live one `shell=True` away from local code execution. Walking through the hardening of `bt-tether-multi` against Bandit B602/B603/B607 — full-path resolution with `shutil.which()`, argv-list invocations, MAC and name validation, and the `# nosec` discipline. The patterns generalize to anything that shells out from Python.
Cover: images/covers/pwnagotchi-plugin-bandit-hardening.png

[TOC]

Pwnagotchi plugins are Python that ships next to a Wi-Fi monitor running as root. They shell out to `nmcli`, `bluetoothctl`, `iw`, `wpa_supplicant`, `curl`. Most plugins on GitHub treat `subprocess` like an `os.system` shortcut: shell strings, relative binary names, untrusted config values concatenated into command lines. None of that survives Bandit's defaults.

This is the hardening pass I did on [`bt-tether-multi`](https://github.com/rivassec/pwnagotchi), the multi-phone Bluetooth tethering plugin I wrote about [last year]({filename}bluetooth-tethering-multi-phone-fallback-for-pwnagotchi.md). The functional behavior — fall back through a list of phones, verify WAN, retry on failure — is unchanged. What changed is that every subprocess call now has a story for why it cannot be tricked, every external value gets validated before reaching argv, and the plugin scans clean against Bandit 1.8.6.

The patterns generalize. If your Python ever calls a binary, the same checklist applies.

## The threat model is local, not remote

The plugin reads phones from `config.toml` on the same disk Pwnagotchi is running from. There is no network input that becomes a shell argument. So why bother?

Two reasons.

First, the Pwnagotchi config file is the highest-leverage attack surface on the device. It is human-edited, it gets shared, plugins copy snippets between machines, and the moment one plugin treats a `name` field as a shell-safe string the whole device class inherits the gap. A field intended to be `"Pixel 8"` that ends up as `"Pixel 8; rm -rf /"` is the entire kill chain. Defense-in-depth says you assume that field is hostile.

Second, you are running as root next to a Wi-Fi adapter. The blast radius of a bug here is the radio. "Local-only" stops being a comforting word the moment you imagine a stranger handed your Pwnagotchi back to you with a "fixed" `config.toml`.

## What Bandit catches that linters miss

Bandit is `pip install bandit` and it ships with rules numbered B602, B603, B607 that are the entire ballgame for `subprocess`:

- **B602** — `subprocess` with `shell=True`. Hard fail unless explicitly suppressed and justified.
- **B603** — `subprocess` without an explicit shell, but the binary path comes from a variable rather than a literal. Bandit can't tell whether that variable is trusted.
- **B607** — starting a process with a partial executable path. `subprocess.run(["nmcli", "..."])` triggers this because `nmcli` is resolved through `$PATH`, and `$PATH` is something you should not trust on a device whose disk has been out of your sight.

Pyflakes, Ruff, mypy will not flag any of these. They are not type or syntax errors. They are policy.

A clean Bandit run on a hardened plugin looks like this:

```text
$ bandit -r bt-tether-multi.py
Run started: ...
Total lines of code: 219
Total lines skipped (#nosec): 6

Total issues (by severity):
        Undefined: 0
        Low: 0
        Medium: 0
        High: 0
```

Six `# nosec` annotations, each one earned. We will get to those.

## Resolve binary paths with `shutil.which()` once, at init

The first move is to stop typing literal binary names into argv lists at all. The plugin's `__init__` resolves every binary it will ever shell out to:

```python
import shutil

class BTTetherMulti(plugins.Plugin):
    def __init__(self):
        self.nmcli = shutil.which("nmcli")
        self.bluetoothctl = shutil.which("bluetoothctl")
        self.curl = shutil.which("curl")
```

`shutil.which()` returns the absolute path of the first match in `$PATH`, or `None` if it is not found. Three things this buys you:

1. **B607 goes away.** Every later subprocess call uses `self.nmcli`, which is `/usr/bin/nmcli`. Bandit sees a literal-looking path argument and shuts up.
2. **Every code path that needs the binary gets a typed "is it installed?" check for free** — `if not self.nmcli: return False`. The plugin degrades cleanly when the underlying tool is missing instead of producing a confusing `FileNotFoundError` from inside an event handler.
3. **The path is locked at startup.** If something rewrites `$PATH` later (a malicious systemd drop-in, a rogue plugin, your own shell config), the plugin keeps using the version that existed when it loaded.

The cost is one `if` check per call site. Tiny.

## Always pass argv as a list. Never `shell=True`.

Every subprocess call in the plugin uses the list form:

```python
subprocess.run(
    [self.nmcli, "connection", "delete", phone_name],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    check=False,
)  # nosec B603
```

The `# nosec B603` is there because Bandit's static analysis sees a variable in `argv[0]`, not a literal string, and it does not trace data flow to know that `self.nmcli` was populated by `shutil.which()` at startup. The annotation is a localized claim: "this argv[0] is a resolved absolute path, here's the structural reason." Each of the six `# nosec` comments in the plugin sits next to a call that is provably bound to a resolved binary path and a list of strings, never a shell.

The list form matters because it bypasses `/bin/sh` entirely. With `shell=True` you are concatenating strings and handing them to a shell that will tokenize them, expand globs, run subshells from `$(...)`, and follow whatever locale-specific rules apply. With a list, the kernel's `execve(2)` gets exactly the argv you passed. No tokenization. No expansion. No glob.

If you find yourself reaching for `shell=True` because you wanted to pipe two commands together, the answer is to call them as two separate `subprocess.run()` invocations and stitch them in Python:

```python
# Wrong
subprocess.run("ip link show | grep wlan0", shell=True)

# Right
out = subprocess.run([self.ip, "link", "show"], capture_output=True, text=True)
matches = [l for l in out.stdout.splitlines() if "wlan0" in l]
```

The list form is also the only form that makes sense once any argument becomes a variable. The moment a `phone_name` from config goes into a string interpolation that goes into a shell, you have a remote-config-execution bug. The list form turns that same value into a single argv slot the shell never sees.

## Validate the inputs that become argv

`shutil.which()` and the list form make the call site safe. They do not make the *arguments* safe. A `phone_name` of `"Pixel 8 Network; reboot"` does not break out of `subprocess`, but it does become a NetworkManager connection profile name with a semicolon in it, which is its own ugly debugging story.

Two validators run before any value reaches argv:

```python
def _sanitize_mac(self, mac):
    if re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac):
        return mac.lower()
    raise ValueError(f"Invalid MAC address: {mac}")

def _sanitize_name(self, name):
    name = name.strip()
    if re.match(r"^[\w\s\-]{1,32}$", name):
        return name
    raise ValueError(f"Invalid phone name: {name}")
```

The MAC regex is restrictive on purpose — six pairs of hex separated by colons, nothing else. The name regex allows word characters, spaces, and hyphens, capped at 32 characters. Both of these reject inputs at config-load time so that the rest of the plugin can assume its values are already clean. The validation lives in `_validate_phones()`, which runs from `on_loaded` and `on_config_changed`. Phones that fail validation are dropped, logged, and never reach a subprocess call.

The pattern is "validate at the trust boundary, trust everything past it." The trust boundary in this plugin is the config-load handler. Past that, the rest of the code is allowed to assume `phone["mac"]` matches `^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$`. That assumption is enforced by the validator, not by hope.

## The `# nosec` discipline

Six `# nosec` annotations is six fewer than zero, but it is still six places where you are telling the auditor "trust me." The discipline that keeps that honest:

1. **Every `# nosec` annotates exactly one call.** No file-level suppressions, no broad ignores. If three calls need it, three `# nosec` comments. Each one is a localized claim.
2. **The reason is structural, not "it works."** The plugin's `# nosec` comments all sit next to calls where the binary path came from `shutil.which()` and the arguments are either literals or inputs that have already passed `_sanitize_*`. That is the structural reason Bandit's flag is a false positive.
3. **`# nosec` annotations are reviewed as code.** When a plugin update changes how an argument flows into a subprocess call, the `# nosec` next to that call gets re-evaluated. If the structural reason no longer holds, the annotation comes off and the call gets fixed.

Bandit also accepts targeted suppressions like `# nosec B603` instead of bare `# nosec`. Targeted is better — it documents which rule you are silencing and avoids accidentally hiding a different finding the next time a rule fires on the same line.

## What this looks like in CI

The plugin's repo runs Bandit on push. The relevant fragment of GitHub Actions:

```yaml
- name: Bandit security scan
  run: |
    pip install bandit==1.8.6
    bandit -r bt-tether-multi.py --severity-level low --confidence-level low
```

`--severity-level low --confidence-level low` is the strictest setting. Anything less and you are filtering out the exact class of finding you want to see. The plugin is small enough that this runs in seconds. The GitHub Actions workflow fails the PR if Bandit returns non-zero, which happens on any unsuppressed finding at any severity.

Pin the Bandit version. Bandit's rule set evolves; an unpinned `bandit` in CI means a future point release can fail your PR for reasons you have not seen before. Bump deliberately, not on every install.

## The pattern generalizes

The four moves — resolve binaries with `shutil.which()` at init, pass argv as lists, validate inputs at the trust boundary, annotate `# nosec` per-call with a structural reason — are not Pwnagotchi-specific. They are the entire defense for any Python that shells out:

- A homelab MCP server that runs `docker exec` on user-supplied container names.
- A CI script that calls `kubectl` against a cluster name from environment.
- A Pelican plugin that runs `convert` on filenames from frontmatter.
- A Discord bot that calls `ffmpeg` on URLs.

Each of these is one `shell=True` away from a shell-injection bug. Each is one resolved-binary-path away from being safe by construction.

The Pwnagotchi case is small enough to be a clean worked example. The plugin is 283 lines. The hardening pass added maybe 40, and most of it is the validators that make the rest of the code shorter because it stops needing defensive checks. Six `# nosec` comments, each one explainable in a sentence. Bandit clean. The radio still tethers.

The reason this matters is not Bandit. Bandit is a tool. The reason is that the same patterns Bandit teaches you in 200 lines of plugin code are the patterns that hold up at 200,000 lines of cloud infrastructure. The IAM equivalent of "validate at the trust boundary, trust everything past it" is what [IAM Roles That Fail Loud]({filename}iam-safe-defaults-fail-loud.md) is about. The shell-injection equivalent at the cluster scope is the [paved-road adoption pattern]({filename}paved-road-adoption-as-control.md). Plugin hardening is just where you can see the whole pattern at once.
