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
