# Agent Security Playbook

## Purpose

Use this playbook for work involving secrets, dependencies, subprocesses, auth, network calls, filesystem access, external input, or generated artifacts.

## Secrets

- Never commit secrets.
- Do not print credentials, tokens, private keys, personal data, or sensitive payloads.
- Use environment variables or the project's configured secret mechanism.
- Treat accidentally exposed secrets as compromised and report the risk.

## Inputs And Trust Boundaries

Validate inputs at trust boundaries:

- CLI arguments
- files from users or external systems
- network responses
- model outputs
- subprocess output
- configuration files

Prefer structured parsers over ad hoc string parsing when formats are known.

## Dependencies

- Do not add dependencies unless justified by scope and maintenance value.
- Prefer mature, widely adopted libraries.
- Avoid adding packages for trivial logic.
- Document user-impacting dependency changes.

## External I/O

For filesystem, network, and subprocess work:

- keep side effects explicit
- handle failures clearly
- avoid destructive defaults
- test error paths when practical
- avoid shell invocation when a structured API is available

## Automation

Security-sensitive checks should be enforced by CI, hooks, scripts, or project commands where practical. Do not rely only on agent memory.
