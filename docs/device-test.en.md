# Steam Deck device testing

[中文](device-test.md)

Use a disposable directory such as `~/DeckAgent/test`. Record plugin version, build ID, SteamOS, Decky, LCD/OLED, and test time. Distinguish browser checks, CEF automation, and physical input. This is a checklist, not a passing test report.

## First installation and updates

- Install the local ZIP with only Decky present; no separate Pi/Node installation should be needed.
- Match frontend/backend versions to the Release and confirm retained settings, providers, history, and voice models.
- Exercise discovery, HTTPS download, SHA-256 verification, native confirmation, and reload from a real GitHub Release. Test cancellation, retry, invalid checksums, and busy-state protection.
- Verify manual local-ZIP instructions when checksums or the installation interface are unavailable.

## Pages and input

- Test entry points from Steam home and game overlay, returning to Steam, and switching conversations.
- Physically test A/B, directions, shoulder buttons, touch, Chinese keyboard input, and focus restoration after dialogs.
- Check readable content, scrolling, visible actions, and an unobstructed composer at 854×534 / 1280×800.
- Check streaming, Markdown, code copying, wide tables, tool results, and reading state.
- An unsent new draft must not create history. Drafts should survive switching, closing, and reopening; retries must not duplicate sessions.

## Models and tasks

- Test real provider connections, model selection, hidden saved API keys, and credential-safe errors.
- Create/read files, execute commands, stop tasks, add follow-up input, and run independent sessions concurrently.
- Restoring history must not replay old tasks. Test submit/cancel behavior for extension confirm/select/input/editor requests.
- Test one actual Skill, extension, and MCP in a disposable directory. Record external dependencies rather than promising universal compatibility.

## Voice and recovery

- Cancellation, network loss, invalid hashes, source changes, and insufficient space must not incorrectly mark models ready.
- Test built-in/external microphone discovery and reconnection. Transcripts must fill only the originating draft without sending automatically.
- Test Chinese, English, and mixed speech. Record audio length, transcription time, memory, and gameplay frame times; download size is not memory use.
- Check temporary recording cleanup after completion/cancellation and state/process recovery after suspend, resume, network loss, and plugin reload.
- Do not describe stopping or interruption as rollback. Inspect actual files to verify external effects.

## Diagnostics and feedback

Run the bundled diagnostic script, verify versions/runtime files, and check log rotation, debug toggling, and redaction. Report Issues with minimal reproduction and necessary evidence, hiding keys, paths, IPs, and private content. See [Debugging](debugging.en.md).


## Built-in player workflows (0.8.0, 2026-11-05)

- All four Skills pass format validation. Real Pi with a local test provider verifies tool/Skill discovery, file operations, cancelled GUI confirmation without writes and confirmed Mod deployment.
- File regression coverage includes configuration backup/restore, Mod ownership and enable/disable/uninstall, interrupted installation recovery, executable bits, plugin retries and HTTP 206/resume.
- Browser validation at 1280×800 covers task drafts, pending plugin installation, retries and handoff parameters, with no horizontal overflow, framework error or unhandled exception. An 854×534 screenshot was not completed this round.
- On Steam Deck, discovery finds 17 Steam games. Real Ludusavi 0.31.0 backs up/restores a newly created isolated test save and restores the pre-restore protection copy; existing game saves are untouched.
- The official 14389479-byte Linux archive and legal.zip pass pinned SHA-256 verification. Device downloads timed out, so this run prefetched official assets on the Mac and transferred them to the isolated test directory. Continue validating direct device download behavior.
- Live web and Topic-scoped searches returned candidates. Complex Mod loaders and actual game startup/graphics results still require per-game testing.

- The 0.8.0 system-Python smoke test did not cover Decky's missing `xml.etree`, so the first deployed backend failed to start. Version 0.8.1 removes this dependency and adds an import regression that simulates the missing XML modules.

- Version 0.8.2 also selects system Python instead of the frozen PluginLoader executable and removes PyInstaller-specific library/startup environment from helper processes. Regression tests execute the helper and simulate a polluted frozen environment.
