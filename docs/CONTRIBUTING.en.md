# Contributing to Deck Agent

[中文](CONTRIBUTING.md)

Installation reports, compatibility results, documentation, and fixes are welcome. Current priorities are reliable installation and device usability. Discuss larger features in an Issue first.

## Reporting issues

Use the Bug or feature template with plugin, SteamOS, Decky versions, and minimal reproduction. For UI problems, distinguish the development browser, Steam home, and game overlay. Report browser/CEF checks separately from physical-controller tests.

Inspect logs/screenshots before sharing; never attach API keys, authentication files, private conversations, or game saves. For security issues, see [Security](SECURITY.en.md).

## Development

Follow [Development](development.en.md) to install locked dependencies. Keep personal configuration and experiments in ignored `.dev-data/`, outside source files and fixtures.

Before submitting:

```sh
npm run typecheck
npm run test:frontend
npm run build
npm test
```

Release changes also require Linux x64 runtime preparation, clean-package smoke testing, and Decky compatibility checks. For UI, focus, voice, or suspend changes, state the actual test environment and untested items.

## Changes and commits

- Keep changes focused and explain the problem, resulting behavior, and verification.
- Write Git commit titles and bodies in both Chinese and English, with Chinese first and matching meanings.
- Preserve dependency sources/licenses and explain new dependencies.
- Real provider requests may cost money. Use temporary directories and the existing faux model for repeatable tests.
- Every package build increments the version; see [Releasing](releasing.en.md).

Contributing code means you have the right to offer it under this project's MIT license. Identify third-party material and its separate license.
