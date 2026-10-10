# Central skill template

Write `<root>/plugin/skills/<slug>/SKILL.md` from this template, then run `site_plugin.py scaffold --site <slug>` (layout in `plugin-layout.md`). Fill every angle-bracket field from
`plan.json` and the program's registry. Keep it lean: the command list and how to call the
program. Detail per command goes into `${CLAUDE_PLUGIN_ROOT}/references/<command>.md` only when a command needs more
than a few lines.

````markdown
---
name: <slug>
description: Automate <Site name> for the user's own signed-in account through a local program; run help for the command list. Use when the user runs /<slug> or /<slug>:<slug>, or asks about their <Site name>: <one phrase per capability, in the user's words, including every write>. <Only when another site skill claims similar requests: Not for <other host> data such as <its items>; use /<other slug> for those.>
argument-hint: "<command> [options]"
---

# <slug>

Request: $ARGUMENTS

The program lives at `<root>/program/` and is called through the plugin's launcher, which runs
`uv run --project <root>/program <slug> --env-file <root>/.env`:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/<slug> <command> [options]
```

It paces itself and classifies failures. Do not call the site any other way, and do not add
retries around it.

## Commands

| Command | Kind | Status | Does |
|---|---|---|---|
| `help` | read | local | Lists commands, inputs, outputs, readiness and session status |
| `<command>` | <read or write> | <verified live, built, not verified, or blocked: reason> | <purpose> |

<Only when several rows share a long status: one or two lines saying what each short status means, such as `blocked: session`, and that each command's full status and log are in `<root>/var/state/readiness.json`.>
Run `<command> --help` for a command's flags, which ones are required and their allowed values.

With no command, or with `help`, run `help` and show its result as a short table.

## Writes

`<write commands>` change account state. Run them with `--dry-run` first, show the user what will
be sent, and run with `--yes` only after the user approves that exact call in chat.

## Errors

| Exit | Class | What to tell the user |
|---|---|---|
| 10 | SessionExpired | Cookies expired. Copy fresh cookies from the browser into `<root>/.env`. |
| 11 | ChallengeRequired | The site wants a human check. Open it in the browser and complete it there. Do not retry. |
| 12 | RateLimited | Slow down. Wait before the next command. Do not retry in a loop. |
| 13 | ApiError | Report the code from stderr. |
| 14 | ContractBroken | The site changed. Run `/webapp-re:engineer <slug> <command>` to rediscover it. |
| 15 | NotPermitted | The account cannot do this. |
| 16 | TransportError | Network problem. The program already retried. A read can be run once more. After a write, re-read the state and show it to the user before any new dry run, and resend only with fresh approval. |

## Provenance

Built by the web automation pipeline on <date> from `<root>/plan/plan.json`. Each command's
endpoints are recorded in `<root>/knowledge/`. Live verification log: `<root>/var/logs/<file>`.
````

## Sub-skills

`<root>/plugin/skills/<group>/SKILL.md` uses the same template restricted to that group's
commands, and the central skill's command table lists the sub-skill instead of its commands.

## Check after writing

- Frontmatter parses, `name` equals the directory name, description under 1024 characters. The description does not list command names; the table and `help` do.
- Every command in `plan.json` that was built appears in the table, and nothing else does.
- `help` output from the program and the table agree on names and kinds.
- The Status column starts with `verified live`, `local`, `built, not verified` or `blocked`. The
  site menu reads it to show each command's state, so keep it current after every live run. Keep
  each status short: a reason repeated on several rows becomes a short status such as
  `blocked: session` plus a line in the legend under the table. There is no Output column; output
  schemas are in the program's registry.
- If `<root>/menu/hints.json` exists, `build_menu.py install --site <slug>` has been run and the
  skill carries the `## Menu` section between its markers.
- `site_plugin.py check --site <slug>` and `claude plugin validate <root>/plugin --strict` pass.
