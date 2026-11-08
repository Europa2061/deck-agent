# Built-in player workflows

[中文](player-workflows.md)

Select a suggestion to fill an editable draft, move the cursor to the end, and open the Steam keyboard. Add your details and send it when ready. You can also describe your task directly or select a Skill.

| Workflow | Built-in capabilities |
| --- | --- |
| Game troubleshooting and settings | Discover Steam libraries including SD cards, inspect selected logs and configuration candidates, preview exact text replacements, back up and restore settings |
| Saves | Ludusavi discovery, previews, per-game backups/restores and history; explicit file/directory backups |
| Mods and translations | Search by requirements, read author instructions, download specified files, inspect archives, preview deployment, protect overwritten files, track ownership, disable/enable/uninstall |
| Decky plugins | Discover repositories within GitHub's `decky-plugin` topic, inspect releases, validate actual plugin ZIPs and hand installation to Decky's native confirmation |

The Skills (`game-care`, `save-care`, `mod-care`, `decky-plugins`) guide tools of the same domains (`deck_games`, `deck_saves`, `deck_mods`, `deck_plugins`). They remain composable with Pi's native file/command tools, other Skills, extensions and MCP. They do not impose a fixed menu or hide general tools.

Built-in configuration changes, restores and Mod mutations ask for GUI confirmation. This does not add a universal approval gate or a filesystem sandbox. Records and backups live in Decky's `deck-agent/player-tools/` data directory. A completed file operation does not prove that a game launches or that graphics/performance improved; verify in the game.

## Saves

Use an existing Ludusavi installation, or prepare the pinned official Linux x64 release 0.31.0 in plugin data, checking fixed SHA-256 hashes and retaining the official legal archive. It is downloaded on demand, not bundled, and needs no sudo.

The initial isolated configuration includes discovered Steam libraries and retains 10 full backups with up to 5 differential backups per full backup; existing tool-specific configuration is preserved. Preview recognized files before backup. For unsupported games, select explicit paths. Before a Ludusavi restore, current progress is protected in a separate directory. Its `before.path` can be passed as `backupPath` to `backups`, `preview_restore` and `restore`. Empty results and partial failures are not reported as success.

Path backups restore individual captured files and retain files created later. A full directory rollback needs a separate reviewed plan. There is no automatic game-exit trigger, Steam Cloud conflict resolution or cloud overwrite.

## Mods

Discover candidates through web search or GitHub, then check the original instructions, game version, loader, dependencies and native/Proton paths. Users may provide names, URLs or archives; there is no fixed supported-game catalog.

The deployment helper handles ZIP/TAR, preserves ordinary execution bits and rejects traversal, duplicate destinations and links. It records overwritten originals and file ownership. Disabling/enabling/uninstalling checks that another program has not changed the files. Changed files require inspecting differences rather than blind overwrites.

The model can use other installed tools for complex loaders, dedicated managers, 7z/RAR or platform authorization. Web discovery uses Bing RSS; blocked access can be handled with revised searches, GitHub or other connected tools. Login, purchase and CAPTCHA requirements remain with the user. A locally recorded hash is not an author-provided checksum.

## Decky plugins

Discovery is scoped to https://github.com/topics/decky-plugin without maintaining a curated catalog. A topic does not establish review, compatibility or store status.

Prepared requests appear in the chat page/sidebar. Select “Continue installation” and confirm through Decky. A request may be retried after cancellation. Source/version records support later verification and updates.

`queued` is not success; `observedInstalled` only matches disk manifests, not successful loading. The installer uses a Decky internal API and retains retry information on failure. Deck Agent's own updates use About & Updates to avoid reloading itself during a task.

## Development

`resources/extensions/player-tools.ts` is loaded with Pi's `--extension` flag. It passes JSON through stdin to `backend/player_tools.py`; domain operations live in `backend/workflows/`. Arguments are not concatenated into shell commands. Cross-process write locks and operation records support recovery.

Run `python3 -m unittest discover -s tests -p test_player_workflows.py -v`. `test_pi_integration.py` exercises real Pi with a local test provider, including tool discovery/calls, Skill discovery and cancelled GUI confirmation. Mocked search/Ludusavi tests alone do not establish external or game compatibility.
