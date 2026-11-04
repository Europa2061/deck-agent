# Debugging

[中文](debugging.md)

Check the installed build before reading logs. Use a browser or CEF for frontend problems and a real Steam Deck for device behavior.

## Build and logs

Settings → About and updates shows the version, build ID, and build time. Settings → General → Diagnostics shows runtime details and directories. A dirty build contains uncommitted changes and must not be described as identical to its recorded commit.

| Content | Typical path |
| --- | --- |
| Plugin | `~/homebrew/plugins/deck-agent/` |
| Log | `~/homebrew/logs/deck-agent/deck-agent.log` |
| Settings and Pi credentials | `~/homebrew/settings/deck-agent/` |
| Sessions, voice, and update cache | `~/homebrew/data/deck-agent/` |

Use the actual paths reported by Decky and diagnostics. Logs rotate across three files of up to 5 MB each. They record startup, tasks, tools, voice, and errors, rather than full conversations, command arguments, tool output, or speech content. Third-party errors still need a privacy review.

Run in the Deck's Konsole:

```sh
bash ~/homebrew/plugins/deck-agent/resources/deck-diagnose.sh
tail -n 100 ~/homebrew/logs/deck-agent/deck-agent.log
```

The diagnostic script is read-only, but its output may contain hostnames, IPs, paths, process arguments, and logs. Redact these before sharing.

For detailed logging:

```sh
mkdir -p ~/homebrew/settings/deck-agent
touch ~/homebrew/settings/deck-agent/debug-log
```

Reload the plugin. To disable detailed logging, delete `debug-log` and reload again. Check Decky's own logs if plugin logging is unavailable.

## Local browser

Start both services using [Development](development.en.md). The token-bearing URL printed by the backend uses real Pi; `?demo` uses visibly labeled simulated data and makes no real model requests. Development data stays in `.dev-data/`.

A browser can validate layout, requests, errors, and drafts, but not Steam-native controller behavior, sound, microphones, or gameplay impact. Check dialogs, scrolling, and the composer at 854×534 and 1280×800.

## SSH and CEF

SSH is for development transfers and inspection, not a requirement for using the plugin. Enable and configure it yourself in desktop mode and check the current LAN address. Never share passwords or private keys in chats or Issues.

Replace `DECK_IP` and `X.Y.Z`:

```sh
ssh deck@DECK_IP
scp out/deck-agent-X.Y.Z.zip deck@DECK_IP:~/Downloads/
```

Then select the local ZIP in Decky. CEF is Steam's browser debugging environment; enable its remote debugging through the current Decky settings and use it only on a trusted network.

### Verified remote update route

First confirm there are no running tasks, pending requests, recordings, or transcriptions, and verify the ZIP's SHA-256. Transfer it through SSH, connect to the device's existing CEF endpoint, and operate Decky's local installation and native confirmation. After reloading, verify frontend/backend versions and retained sessions/settings. Use current addresses and ports; submitting an installation request does not prove success.

Example CEF tunnel, using device port 8081:

```sh
ssh -N -L 127.0.0.1:18081:127.0.0.1:8081 deck@DECK_IP
node scripts/check_gamepad_navigation.mjs http://127.0.0.1:18081
```

The navigation script moves focus without clicking or sending messages. Physical controller checks are still required; see [Device testing](device-test.en.md).

## Packaging boundaries

Use `scripts/package.py`, `smoke_package.py`, and `decky_compat_report.py` for packaging, clean-extraction startup/tool verification, and Decky loading checks. The official CLI's standard whitelist does not cover this project's backend, runtime, resources, and docs; it cannot directly replace this packaging flow.

References: [Decky template](https://github.com/SteamDeckHomebrew/decky-plugin-template), [Decky Wiki](https://wiki.deckbrew.xyz), [Valve device debugging](https://partner.steamgames.com/doc/steamhardware/loadgames).
