# Permissions, data, and privacy

[中文](privacy.md)

This describes the current implementation. Your providers and extensions have their own terms.

## Agent permissions

Pi uses file and command tools with its running user's permissions. The plugin does not request root or automatically install system dependencies with sudo. This is not an operating-system sandbox; accessible files outside the working directory may be read or changed.

The plugin follows Pi's tool/extension behavior and does not add universal approval for dangerous operations. An extension confirmation does not mean every command asks first. Stopping does not roll back completed actions.

## Network activity

| Operation | Recipient and data |
| --- | --- |
| Connection tests, chats, and tasks | Your configured provider receives authentication, relevant conversation context, and included file/tool results, as determined by Pi, the model, and extensions |
| Voice model downloads | Hugging Face or the selected hf-mirror; the service sees IP/download requests, and fixed-version files are verified |
| Update discovery and downloads | GitHub API and Release download endpoints; repository/package requests, without needing chat content or model API keys |
| Skills, extensions, MCP, and external commands | Tool-dependent services; inspect their sources before installation |

The plugin currently has no active usage-analytics upload feature. Receiving services apply their own policies to normal requests. Sending a locally transcribed draft submits its text to the configured model.

## Local data

Typical paths, subject to Decky's actual configuration:

| Directory | Contents |
| --- | --- |
| `~/homebrew/settings/deck-agent/` | Plugin settings and Pi authentication/model/extension configuration under `pi/` |
| `~/homebrew/data/deck-agent/` | Session history/metadata, new drafts, voice models/downloads/recordings, and update cache |
| `~/homebrew/logs/deck-agent/` | Rotating plugin logs, currently up to about 15 MB |

Credentials are stored in local files with `0600` write-time permissions, not encrypted storage. Same-user processes, trusted extensions, and higher-privilege users may read them. Backups may also contain plaintext credentials.

Recordings are removed after transcription or cancellation; crashes may leave temporary files. Conversations/drafts persist, and code updates do not intentionally clear them. Cancelled voice downloads may retain partial files for resumption; cancelled/failed update downloads remove partial packages.

## Logs and reports

Plugin logs are designed to exclude full conversations, command arguments, tool output, and speech content, and to redact registered secrets. Third-party errors/process output and diagnostics can still expose private details; automatic redaction is not comprehensive.

Before filing an Issue, inspect logs, recordings, and screenshots. Hide keys, usernames, private paths, hostnames, IPs, private provider endpoints, and conversation content. Do not upload authentication files or whole settings/data directories. Revoke exposed credentials with the provider before reporting a leak.


## Built-in player tools

Operation records, Mod ownership, original-file backups, plugin requests and the on-demand Ludusavi installation are stored in Decky's `deck-agent/player-tools/` data directory. Backups may contain personal data; tool results read by the model enter your configured provider's context.

Mod web discovery sends search terms to Bing; repository/release discovery uses GitHub. Author pages and downloads connect to their respective hosts. Search terms should contain game requirements rather than private logs or credentials.

These dedicated tools request GUI confirmation before configuration changes, restores and Mod mutations. Plugin installation uses Decky's native confirmation. This is not a universal approval gate or sandbox for Pi's native tools or third-party extensions.
