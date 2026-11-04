# Installation and first use

[中文](installation.md)

## Requirements

- Decky Loader.
- A working LLM API (endpoint, API key, and model).

Model requests may cost money, including the short connection test. Voice models are downloaded separately when needed.

A public release repository has not been configured yet. Once available, download `deck-agent-X.Y.Z.zip` and its `.zip.sha256` from this project's Releases. The Source code ZIP is not installable. Replace X.Y.Z and run `sha256sum -c deck-agent-X.Y.Z.zip.sha256` in the download directory to verify it.

## Installation

1. Finish running tasks, recordings, and pending requests.
2. Enable developer options in Decky settings and select the downloaded local ZIP. Button names may vary by Decky version.
3. Open Settings → About and updates to verify the version. If loading fails, reload the plugin or restart Decky, then see [Debugging](debugging.en.md).

Normal use requires neither SSH/CEF nor development tools.

## First task

1. Add a provider, API key, and model, then test the connection. A custom endpoint must support the selected provider protocol.
2. Create a disposable directory in desktop mode, such as `~/DeckAgent/test`, and select it for a new conversation.
3. Ask: “Create hello.txt in the current directory containing Hello Deck, then read it back.” Inspect both the file and response.
4. Learn stopping, switching conversations, and draft recovery before using your own working directories.

The working directory does not limit the agent's file permissions. A prompt saying “only use this directory” is not a security boundary.

## Voice

Select a voice model and download source, wait for file verification, then choose a microphone. Models use additional storage. Recording is transcribed locally, filling the draft without sending it automatically.

Use the UI for current model sizes, languages, and free-space requirements. Complete Steam Deck comparisons of speed, power consumption, and gameplay impact are not available yet; start with a short recording while idle.

## Updates

1. In About and updates, enter this project's `owner/repo`, once announced, and check for updates.
2. Read the release notes, then use Download update. Progress, cancellation, and retry are supported. Completed downloads are checked against SHA-256 and package versions.
3. Finish tasks, pending requests, recordings, and transcriptions. Choose Install downloaded update and confirm in Decky's native dialog. Do not start tasks while confirmation is open.
4. Reopen the plugin and verify its version, conversations, provider settings, and voice models.

In-plugin downloads require a matching `.zip.sha256`. If the installation interface is unavailable, use Manual installation to open the release page, download the ZIP, and select it locally in Decky. Restarting the plugin requires downloading the update again.

Update checks prefer stable releases. When none exist, a public prerelease with a matching package can be returned. After a stable release exists, checks stay on that channel. Empty/private repositories and GitHub rate limits are reported in the UI.

Updates do not intentionally overwrite persistent data. Before important updates, back up `~/homebrew/settings/deck-agent/` and `~/homebrew/data/deck-agent/`; these backups contain credentials and conversations.

## Uninstalling and restoring

Uninstall through Decky settings. The plugin's unload logic retains settings, history, and models, but Decky's data cleanup behavior may vary. Reinstall to restore the plugin and check retained data.

For complete removal, exit the plugin, back up your data, and inspect its `deck-agent` settings/data/log directories. Deleting these loses credentials, sessions, models, or logs; no one-command deletion is provided here.

## Known limitations

- OLED is the primary development device; LCD and other SteamOS/Decky combinations need testing.
- Controller, Chinese keyboard, voice quality, suspend/resume, and gameplay behavior need continued validation.
- Entering the full page from a game overlay may require returning to Steam home first.
- Git, uv, system libraries, and TUI-only extensions depend on the device environment.
- Stopping does not undo writes or guarantee that all external command effects disappear.
- Speech recognition is local; online model tasks still require a connection.

## Troubleshooting

Record the version, time, reproduction steps, and error. In the Deck's Konsole, run:

```sh
bash ~/homebrew/plugins/deck-agent/resources/deck-diagnose.sh
```

Review output for hostnames, IPs, paths, process arguments, and private logs before sharing. Do not upload `auth.json`, whole data directories, or private conversations. See [Debugging](debugging.en.md).
