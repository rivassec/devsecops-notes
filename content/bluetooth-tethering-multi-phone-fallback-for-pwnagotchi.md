Title: Bluetooth Tethering with Multi-Phone Fallback for Pwnagotchi
Date: 2025-07-22
Category: Projects
Tags: pwnagotchi, bluetooth, plugin, networking, python
Slug: bt-tether-multi
Author: rivassec
Summary: A custom Pwnagotchi plugin for rotating Bluetooth tethering connections with fallback and WAN validation.

## Problem

If you're running a [Pwnagotchi](https://pwnagotchi.ai) in the field, you've probably run into tethering issues — like forgetting to bring your "main" phone or finding that the current tether connection silently lost WAN access. The default Bluetooth tethering plugin doesn't gracefully handle failover or WAN state validation.

## Solution

`bt-tether-multi` is a custom plugin I wrote to solve that. It allows your Pwnagotchi to:

- **Connect to multiple phones via Bluetooth tethering** — with configurable priority
- **Detect loss of WAN access** (e.g., portal redirect or signal loss)
- **Automatically rotate** to the next available configured phone
- **Avoid looping** rapidly through phones by enforcing a retry delay
- **Show the connection state** on the UI

## How It Works

When the plugin is loaded, it checks for a list of phones defined in the config (name, MAC, IP, and OS type). If the active tether loses internet access, the plugin tries the next phone. It uses `nmcli` to manage connections and `curl` to verify WAN access.

Here's what shows up on the UI:

- `B:<name>` — Connected to a known phone
- `B:???` — Connected, but not recognized
- `...` — Rotating through connections
- `X` — Disconnected
- `!` — Config or plugin error

The phone list is prioritized based on order, and WAN connectivity is verified using a fast `curl --max-time 3` check to `https://www.google.com`.

## Installation

Place the plugin in your Pwnagotchi custom plugin folder and define your phones in `config.toml`. A full example is available in the [GitHub README](https://github.com/rivassec/bt-tether-multi).

## Security Considerations

The plugin was scanned with [Bandit](https://bandit.readthedocs.io), and only low-severity subprocess warnings remain. All commands are built without `shell=True`, with strict input sanitation on MAC addresses and phone names.

## Final Thoughts

This plugin is aimed at people who bring multiple devices into the field and want their Pwnagotchi to remain as autonomous as possible. It’s saved me plenty of headaches, and I hope it helps others too.

You can find the source and README here: [rivassec/bt-tether-multi](https://github.com/rivassec/bt-tether-multi)
