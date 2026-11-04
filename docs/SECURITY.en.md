# Security

[中文](SECURITY.md)

The project is in early testing and currently maintains the latest source/release, without promising security fixes for older versions.

## Reporting

**Use Issues directly for ordinary bugs, installation problems, and feature requests.**

For vulnerabilities involving data exposure or permission bypass, prefer Security → Report a vulnerability. If unavailable, open an Issue asking for a private reporting route without publishing exploit details, keys, or private data.

Include affected versions, environment, impact, and a minimal reproduction using disposable files. Revoke or rotate exposed credentials with the provider first. No fixed response time is promised.

## Boundaries

The agent can operate files and commands with its running user's permissions. Extension sources and tool behavior affect safety. There is no operating-system sandbox or universal operation-approval guarantee. See [Permissions and privacy](privacy.en.md).
