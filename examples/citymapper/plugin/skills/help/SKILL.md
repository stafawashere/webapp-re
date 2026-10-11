---
name: help
description: "List the citymapper.com program's commands with their kind and readiness, and the session status. Shortcut for /citymapper:citymapper help."
argument-hint: "[command name]"
disable-model-invocation: true
---

# citymapper help

Arguments: $ARGUMENTS

Run `${CLAUDE_PLUGIN_ROOT}/scripts/citymapper help` and show its result as a short table. When the arguments name a
command, run `${CLAUDE_PLUGIN_ROOT}/scripts/citymapper <command> --help` instead and show its flags. Every other
command, and the rules for writes and errors, are in `${CLAUDE_PLUGIN_ROOT}/skills/citymapper/SKILL.md`;
read it before running anything else.
