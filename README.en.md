# Deck Agent

Use an AI agent from Steam Deck's game mode to work with files, run commands, and manage multiple conversations. Built on Decky and [Pi](https://github.com/earendil-works/pi), with streaming replies, Skills, extensions, MCP, and optional local speech recognition.

[中文](README.md) · [Installation](docs/installation.en.md) · [Privacy](docs/privacy.en.md) · [Development](docs/development.en.md) · [All docs](docs/index.en.md)

## Requirements and installation

- Decky Loader.
- A working LLM API (endpoint, API key, and model).

A public release repository has not been configured yet. Once releases are available:

1. Download `deck-agent-X.Y.Z.zip` from this repository's Releases. The automatic Source code ZIP is not an installable plugin.
2. Enable developer options in Decky settings and select the downloaded local ZIP.
3. Open Deck Agent, add a provider, enter your API key, select a model, and test the connection.
4. Create a conversation and start with a disposable directory such as `~/DeckAgent/test`.
5. For voice input, download a model in voice settings and select a microphone. Transcribed text goes into your draft; you send it yourself.

## Status and limitations

This is a test version, primarily validated on Steam Deck OLED with Decky 3.3.1. Other configurations have not been fully validated.

Physical controller navigation, Chinese keyboard behavior, real provider tasks, speech recognition quality and performance during gameplay, suspend/resume, and public release updates still need further validation. TUI-only extensions and tools requiring external system dependencies are not guaranteed to work.

## Permissions and privacy

The agent can read and modify files and execute commands with the permissions of its running user. There is no filesystem sandbox. Stopping a task does not undo completed changes. Use a test directory and avoid important saves or configuration files during initial testing.

Your configured provider receives relevant conversation content and tool results. Speech recognition runs locally, but sending its transcript to an online model is a network request. API keys, settings, history, and voice models are stored in Decky's persistent directories; plugin updates do not intentionally overwrite them. Temporary recordings are removed after transcription or cancellation.

Check logs and screenshots before sharing. Do not upload API keys, authentication files, or private conversations.

## Contributing and security

Report bugs through repository Issues with plugin, SteamOS, and Decky versions and reproduction steps. See [CONTRIBUTING.md](docs/CONTRIBUTING.en.md). Use Issues for normal bugs and feature requests. For vulnerabilities involving data exposure or permission bypass, see [SECURITY.md](docs/SECURITY.en.md).

## License

Project-owned source is [MIT licensed](LICENSE). Dependencies and voice models retain their respective licenses; see [third-party notices](docs/THIRD_PARTY.en.md). Voice weights are not included in the plugin ZIP.

This is a community project, not affiliated with Valve or the Decky team.
