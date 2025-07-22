Title: Never Lose Connection: Multi-Phone Bluetooth Tethering for Pwnagotchi
Date: 2025-07-22
Category: Projects
Tags: pwnagotchi, bluetooth, plugin, networking, python, hacking, automation
Slug: bt-tether-multi
Author: rivassec
Summary: Enhance your Pwnagotchi's autonomy with `bt-tether-multi`, a custom plugin offering intelligent multi-phone Bluetooth tethering, automatic WAN failover, and robust connection management.

## The Common Pwnagotchi Tethering Problem

If you're an active Pwnagotchi user, you've likely faced the frustration of losing internet connectivity in the field. Whether you forgot your primary tethering phone, moved out of range, or encountered a "silent disconnect" where your phone still reports a connection but lacks actual WAN access (like a captive portal redirect), the default Bluetooth tethering often leaves your Pwnagotchi stranded. This means missed opportunities for handshakes and updates.

## Introducing `bt-tether-multi`: Your Pwnagotchi's Ultimate Network Backup

I built `bt-tether-multi` to make Pwnagotchi networking resilient and autonomous. This plugin empowers your device to:

* **Intelligently Connect:** Configure a list of multiple phones, prioritized by your preference, for seamless Bluetooth tethering.
* **Proactive WAN Detection:** Detect actual loss of internet access (not just Bluetooth connection) using real-world checks.
* **Automatic Fallback:** Gracefully switch to the next available phone in your list if the current connection drops or loses WAN.
* **Smart Retries:** Implement a configurable retry delay to prevent rapid, unproductive cycling through phones during temporary network issues.
* **Clear UI Feedback:** Provides immediate visual cues on the Pwnagotchi's e-ink display about its tethering status.

## How It Works Under the Hood

`bt-tether-multi` integrates directly with your Pwnagotchi's system. Upon loading, it reads your carefully defined list of tethering phones from the `config.toml` file. This configuration includes essential details like the phone's name, MAC address, IP address, and operating system type (Android or iOS) to ensure correct gateway settings.

The plugin leverages standard Linux networking tools:
* **`nmcli` (NetworkManager CLI):** Used to programmatically manage Bluetooth connections, including adding, deleting, and bringing up/down network interfaces for your paired phones.
* **`curl`:** Employed for a fast (`--max-time 3`), non-intrusive check to `https://www.google.com` to verify genuine WAN connectivity. If `curl` can't reach the internet, the plugin considers the WAN lost.

### UI Status Indicators:
The Pwnagotchi's display provides immediate feedback:

* `B:<name>`: Successfully connected to one of your configured phones. The name is truncated for display.
* `B:???`: Bluetooth is connected, but the active phone is not recognized in your configured list. This might indicate an unexpected connection or a misconfiguration.
* `...`: The plugin is currently in the process of rotating through connections or attempting to establish one.
* `X`: Disconnected from all configured phones.
* `!`: A configuration error or plugin-related issue has occurred.

The sequential fallback and retry logic ensure that your Pwnagotchi stays online with minimal intervention, rotating through your devices until a stable internet connection is found.

## Installation and Configuration

Installing `bt-tether-multi` is straightforward:

1.  **Download:** Place the plugin file (`bt.py` from the GitHub repository) into your Pwnagotchi's custom plugin directory (typically `/etc/pwnagotchi/custom-plugins/`).
2.  **Configure:** Add your phone details to your `config.toml` file. Here's a simplified example of what your `config.toml` might look like:

    ```toml
    main.plugins.bt-tether-multi.enabled = true
    main.plugins.bt-tether-multi.phones = [
      { name = "MyAndroid", mac = "XX:XX:XX:XX:XX:XX", ip = "192.168.44.44", type = "android" },
      { name = "MyiPhone", mac = "YY:YY:YY:YY:YY:YY", ip = "172.20.10.10", type = "ios" },
    ]
    main.plugins.bt-tether-multi.retry_delay = 180 # Optional: customize retry delay (seconds)
    ```
    **Important:** Replace `XX:XX:XX:XX:XX:XX` and `YY:YY:YY:YY:YY:YY` with your actual phone MAC addresses. Ensure your IP addresses match what your phone assigns to the Pwnagotchi's Bluetooth interface.

For a comprehensive guide and the most up-to-date configuration examples, please refer to the [GitHub README](https://github.com/rivassec/bt-tether-multi) in the repository.

## Security Considerations

As with any tool that interacts with your system's networking, security is paramount. This plugin has been rigorously scanned with [Bandit](https://bandit.readthedocs.io), a leading Python security linter.

The scan reported "Low Severity" warnings primarily related to the use of the `subprocess` module. It's crucial to understand why these are considered acceptable in this context and how they're mitigated:

* **No `shell=True`:** All external commands (`nmcli`, `curl`, `bluetoothctl`) are executed with `shell=False`. This is a critical security measure as it prevents arbitrary shell command injection by treating all arguments as literal strings, not executable code.
* **Full Paths for Executables:** The plugin now uses `shutil.which` to dynamically determine and use the **absolute file path** for `nmcli`, `curl`, and `bluetoothctl`. This prevents malicious executables from being run if a compromised `PATH` environment variable is present.
* **Strict Input Validation:** All dynamic inputs (like `MAC addresses`, `phone names`, and `IP addresses`) coming from your `config.toml` are subjected to strict regular expression and `ipaddress` module validation *before* being passed to `subprocess` commands. This ensures that only well-formed and safe values are used.
* **Controlled Environment:** Pwnagotchi runs in a specific, often isolated, environment. While caution is always advised, the risk surface is contained compared to a general-purpose server.

The "Low Severity" warnings are primarily general advisories about the *potential* for misuse of `subprocess`, rather than indicative of a direct, exploitable vulnerability in this specific implementation, given the defensive measures taken.

## Final Thoughts

`bt-tether-multi` is designed for the Pwnagotchi enthusiast who values uptime and autonomy. It transforms a common point of failure into a robust, self-managing solution. No more restarting your Pwnagotchi or manually re-tethering when your connection goes south.

This plugin has become an indispensable part of my Pwnagotchi setup, saving me countless headaches in the field. I invite you to try it out and contribute to its development!

Find the source code, detailed installation instructions, and contribute to the project on GitHub: [rivassec/bt-tether-multi](https://github.com/rivassec/bt-tether-multi)
