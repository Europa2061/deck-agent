# Releasing a new version

[中文](releasing.md)

Pushes and PRs run automatic checks. For a release, select the version increment and let CI create a draft with assets; publish it after device acceptance.

## Initial setup

1. Choose the public repository, history policy, and author identity. Push reviewed source to the default branch and enable Issues.
2. Allow workflows to request `contents: write`. Check branch/ruleset permissions for the release bot. The workflow does not bypass protection or force-push; denied writes fail without creating a draft.
3. Wait for **Check Deck Agent** to pass. The local repository currently has no remote, and the new workflow has not run on GitHub yet.

Use the repository-provided `GITHUB_TOKEN`; no personal token is required. See [GitHub authentication](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token).

Current [Decky policy](https://github.com/SteamDeckHomebrew/wiki/blob/main/plugin-dev/submitting-plugins.md#ai-llms-and-so-on) rejects LLM-focused plugins. Distribution uses GitHub Releases and manual local ZIP installation.

## Each release

1. Finish features, bilingual changelog entries, and review, then merge into the default branch.
2. Open Actions → **Release Deck Agent** → Run workflow. Choose the default branch, patch/minor/major increment, and whether this is a prerelease. Use patch for fixes, minor for compatible features, and major for incompatible changes.
3. Wait for CI to automatically:
   - run type, frontend, Python, and bilingual documentation checks and prepare the Linux x64 runtime;
   - increment the version, create a bilingual version commit, and package once;
   - verify clean extraction/startup, real tool execution, Decky loading, versions, and SHA-256;
   - upload the candidate and atomically push its version commit/tag;
   - create a Release draft with ZIP/checksum assets and generated notes.
4. Download from Actions artifacts or the draft and test on Deck. Check versions, real tasks, input/voice, and retained data using [Device testing](device-test.en.md). CI cannot replace physical-controller or actual voice acceptance.
5. Edit the draft with bilingual user-facing notes and known limitations, then click **Publish release**. Verify the public download and in-plugin upgrade. Full upgrade testing requires an older installed version; the same version only verifies the up-to-date state.

There is no manual version.patch application, version commit, tagging, or asset upload. Packaging follows the version commit, so the package source ID matches the tagged commit.

The workflow has build and draft jobs. If only draft creation fails after packaging/pushing succeeded, use **Re-run failed jobs** to retry draft with the same artifact rather than rebuilding. Published releases are not overwritten.

## Failures and concurrency

- Only one release runs at a time. If the default branch advances and the fast-forward push fails, the version commit and tag are rejected together. Start a new run from the latest default branch; no other work is overwritten.
- Failed build checks do not push versions/tags or create drafts.
- Retrying draft may complete assets only while the release remains a draft; it exits if already public.
- Actions artifacts expire after 30 days. User downloads should use Release assets.
- Code, prompt, or runtime-resource changes require a new version candidate rather than replacing a published package.

## Optional local Linux x64 build

```sh
npm ci --ignore-scripts
npm run typecheck
npm run test:frontend
npm run build
python3 scripts/prepare_runtime.py
npm test
npm run package -- --bump patch
python3 scripts/smoke_package.py
python3 scripts/decky_compat_report.py
python3 scripts/verify_release.py
```

Ordinary local packaging increments the version without committing, pushing, or publishing. CI's `--commit-version` requires a clean worktree and commits the version before packaging; it refuses uncommitted local work. Every package still increments its three-part version.

## User updates and rollback

Attach `deck-agent-X.Y.Z.zip` and `.zip.sha256`; neither Source code ZIPs nor outer Actions artifact ZIPs are installable. Discovery prefers stable releases, using the highest matching test version among the latest 100 records only when no stable release exists. Stable users are not automatically moved to prereleases.

The plugin verifies downloads and hands local installation to Decky's native confirmation. Local ZIP installation remains available on failure. Verify the reopened version rather than assuming request submission means success. Rollback can install an older package, but old code may not understand newer data; back up settings/history before important updates.

References: [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository), [gh release create](https://cli.github.com/manual/gh_release_create).
