# Security

[简体中文](SECURITY.zh-CN.md) | **English** | [Home](README.en.md)

FontGuard processes potentially untrusted files. Keep dependencies current and
run CI with minimum permissions. The scanner skips filesystem symlinks, bounds
file sizes and Office XML expansion, disables XML external entities, and never
fetches URLs during scanning. These checks are not a complete parser sandbox;
use an isolated process/container for hostile inputs.

`.fontguard.yml`, `fontguard.lock`, baselines and the local cache are trusted
organization inputs. Protect them with code review. Use `--no-cache` in untrusted
workspaces. Analyzer plugins execute Python code and are opt-in via `--plugins`.

Report reproducible security issues privately to the repository maintainer using
GitHub private vulnerability reporting on the repository's Security tab.
Do not put exploit documents containing private data in a public issue. This
project has no official security email or response SLA.
Include affected versions, reproduction steps, actual impact and a minimal
fixture without sensitive data when reporting an issue.
