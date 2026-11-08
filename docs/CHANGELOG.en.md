# Changelog

[中文](CHANGELOG.md)

## Unreleased

- Upgrade Pi coding-agent and pi-ai to 1.5.0.
- Clarify Issue-based feedback and simplify requirements to Decky Loader and an LLM API.
- Keep public documentation in docs with Chinese/English editions; retain internal research/prototypes and AGENTS.md locally outside Git.
- Remove the LAN installation server and URL-installation entry points; keep local ZIP installation and in-plugin updates.
- Write the appended Deck Agent system prompt in English while retaining its default Chinese response behavior.
- Add user, privacy, contribution, security, release, and third-party documentation plus Issue/PR templates.
- Automatically check pushes/PRs and increment/commit versions, build/verify, tag, and create Release drafts with assets; retry draft separately.
- Confirm the Paraformer original model publisher declares Apache-2.0 in its official API and README.
- Add release-file consistency checks and prerelease discovery when no stable release exists.

## 0.6.1

- Add in-plugin update downloads, progress, cancellation, and retry.
- Verify SHA-256, ZIP paths, plugin identity, and versions; recheck cache integrity and busy state before installation.
- Integrate Decky's native confirmation and local-package installation, retaining manual instructions.
- Development records cover installation and frontend/backend version checks on Steam Deck / Decky 3.3.1 with retained conversations/providers. Real GitHub downloads remain unverified until public releases exist.
- 0.6.0 was a local validation build; 0.6.1 corrected installation button text.

## 0.5.1

- Align composer buttons at 32px with transparent backgrounds and focus borders.
- Local build/UI checks were recorded; this version's device installation was not completed in that test round.

## 0.5.0

- Unify the gray theme and adjust the sidebar/recent conversations.
- Store new conversations as drafts until their first send.
- Record native Decky installation, version, and page checks. Physical input, sound, and recording performance were not fully accepted.

## Player workflows (unreleased)

- Four discoverable Skills and dedicated tools cover game troubleshooting/settings, save management, Mods and off-store Decky plugins while retaining Pi's general tools.
- Add file backups/restores, Mod file ownership and enable/disable/uninstall, Topic-scoped discovery, generic native Decky installation handoff and retry UI.
- Prepare pinned Ludusavi 0.31.0 on demand with official SHA-256 verification; protect current saves before restore and expose recovery of that protected copy.
- Support partial-content downloads, retry/resume and reuse of verified cache entries.
