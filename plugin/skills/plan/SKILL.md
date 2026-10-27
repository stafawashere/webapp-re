---
name: plan
description: "Plan a site's automation program and its plugin from the scope: command set, schemas, dependencies, build order, written to plan/plan.md and plan/plan.json. Makes no requests to the site. Use when the user runs /webapp-re:plan or asks to plan a client, CLI or skill for a scoped site."
argument-hint: "<site slug>"
---

# webapp-re plan

Plugin root: `${CLAUDE_PLUGIN_ROOT}`. Paths written `${CLAUDE_PLUGIN_ROOT}/...` here and in the reference files are under that directory. The arguments are: $ARGUMENTS

Target: the site given after the subcommand.

Second stage of the web automation pipeline. Reads `scope/scope.json` from the site directory and
writes `plan/plan.md` and `plan/plan.json`, which `/webapp-re:engineer` executes.
This stage makes no requests to the site.

## Steps

1. **Find the site.**
   `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/kb.py path --site <target>`.
   If `scope/scope.json` is missing, stop and suggest `/webapp-re:scope <target>` first.
2. **Load context.** Do not read `scope/scope.json` whole (40 to 240 KB on existing sites).
   `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/scope_query.py <root>/scope/scope.json` prints a
   one-line-per-item index (7 to 14 percent of the file), then `--id <item>` opens one item,
   `--section auth` one section and `--grep <regex>` finds item ids. Read `scope/scope.md`, the
   site's `knowledge/INDEX.md`, and any existing `plan/plan.json` (extend it rather than replace
   it, and keep command names stable, since users may already type them). For the status ladder
   and contract fields, read the "Status ladder" section of
   [references/knowledge-base.md](${CLAUDE_PLUGIN_ROOT}/references/knowledge-base.md), not the whole reverse stage.
3. **Ask what matters**, only if the user did not say: which capabilities they want first, whether
   writes are in scope at all, and the output they want by default (JSON or a table). One short
   message, then proceed with sensible defaults if they do not answer.
4. **Design the command set** by the rules in
   [references/command-design.md](${CLAUDE_PLUGIN_ROOT}/references/command-design.md): one command per user-level
   capability, grouped into sub-skills only when a group has its own setup or its own risk level,
   and always a `help` command.
5. **For each command, write**: name, one-line purpose, read or write, inputs and outputs as JSON
   Schema, the endpoints it depends on (by scope endpoint id and, where one exists, knowledge base
   finding id), pagination behaviour, the failure classes it can raise, the confirmation rule for
   writes, and the open reverse-engineering work with an estimated live-request budget.
6. **Order the build** so each step unlocks the next: session adoption and the transport first,
   then the read that proves auth works, then reads that share endpoints, then pagination, then
   writes, and last anything blocked on signing or obfuscation. Mark each step's exit check.
7. **Write** `plan/plan.json` in the format in
   [references/plan-format.md](${CLAUDE_PLUGIN_ROOT}/references/plan-format.md) and `plan/plan.md` for a person.
8. **Check.** `uv run --script ${CLAUDE_PLUGIN_ROOT}/scripts/check_plan.py <root>`
   validates the plan against the scope (every dependency exists, every command has schemas, no
   duplicate names, build order covers every command). Fix until it passes, and quote its last
   line in the reply.

## Reply

The command list as one table (name, read or write, status of its endpoints), the count of open
reverse-engineering steps and their request budget, the risks, and the path to `plan.md`. Then
suggest `/webapp-re:engineer <slug>`.

## Example shape

For a site with the slug `example` the central skill is `/example`. `/example help` prints every
command, its inputs, outputs and readiness. `/example fetch-saved-items` returns
`{ "items": [ { "id", "name", "price", "saved_at", "status" } ] }` from the user's saved list.
A write such as `/example save-item <id>` is planned with a confirmation step and is built
last.
