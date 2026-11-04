# Development and builds

[中文](development.md)

## Local development

Use Node.js 22.19 or newer and Python 3.11 or newer.

```sh
npm ci --ignore-scripts
npm ci --prefix runtime
npm run typecheck
npm run test:frontend
npm run build
npm test
```

Start these in separate terminals:

```sh
python3 scripts/dev_server.py
```

```sh
npm run dev
```

Open the token-bearing local URL printed by the backend. The browser adapter uses regular controls with real Pi requests; production uses native Decky controls. `?demo` is the explicitly labeled simulated preview.

Development data is isolated in Git-ignored `.dev-data/`. Do not commit real credentials. The development HTTP server binds only to `127.0.0.1` and requires a random token; neither the server nor development data ships in the plugin.

## Linux x64 packages

Mac-installed runtime dependencies are not marked distributable. Build on Linux x64 or use GitHub Actions:

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

Every package operation increments the version and synchronizes the root manifest/lockfile. Use minor for compatible features and major for incompatible changes; see [Releasing](releasing.en.md). Outputs are `out/deck-agent-X.Y.Z.zip` and `.zip.sha256`, with one `deck-agent/` root containing metadata, backend, frontend, runtime, resources, public docs, and licenses. Weights, internal records, prototypes, tests, and credentials are excluded.

Runtime preparation verifies official Node/sherpa-onnx hashes, installs locked Pi dependencies, and checks Pi/STT startup before writing a Linux release marker. Packaging rejects missing or inconsistent runtime versions. On first load, the plugin restores links and executable permissions that Decky's ZIP extraction does not preserve. The smoke test uses clean extraction and a real Pi tool call.

Pushes and PRs run Check Deck Agent. Manually dispatched Release Deck Agent increments/commits the version, builds/verifies packages, tags the commit, and creates a draft with assets; publish after device acceptance. A Linux container is another option; use an ordinary container user and mount only the project.

## Pi dependency

Pi coding-agent and pi-ai are pinned to **1.5.0** in `runtime/package.json` and its lockfile. After upgrades, reinstall/test real tools and history recovery, then prepare the release runtime again on Linux x64. Never reuse a stale release marker from older or Mac-installed dependencies.
