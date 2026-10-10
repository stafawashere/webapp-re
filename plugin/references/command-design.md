# Command design

## Granularity

- One command per thing a user would say in one sentence: "show my saved items", "get this
  thread", "download my invoices for March". Not one per endpoint, and not one per page.
- A command that needs two endpoints (resolve a name to an id, then read) is still one command.
  Record both dependencies and the request cost.
- List commands page by default up to a `--limit`, and expose `--cursor` so a caller can resume.
- Prefer `fetch-*` for reads that return a collection, `get-*` for one item, `search-*` for
  queries, and plain verbs (`add-*`, `remove-*`, `send-*`, `update-*`) for writes. Kebab case.

## Sub-skills

The central skill is `/<slug>:<slug>`, the main skill of the site's plugin. Split it into
sub-skills only when a group of commands has its own setup (a second account, a different
origin), its own risk level (writes that others can see), or would push the central SKILL.md past
a few hundred lines. A sub-skill is a skill named `<group>` in the same plugin, so it runs as
`/<slug>:<group>`, and the central `help` lists it. Naming rule in `plugin-layout.md`.

## help

Always present. Prints, from the program's own registry rather than from prose, every command
with its one-line purpose, inputs, output schema name, read or write, and readiness
(`ready`, `partial`, `blocked: <reason>`). It also prints the session status (cookies present,
last successful request) without printing any cookie value.

## Outputs

Every command returns JSON on stdout by default, matching its output schema, with a
`--format table` alternative for people. Errors go to stderr as JSON with a `class` field from
the failure classes, and each class has its own exit code. A caller never parses prose.

## Writes

Every write command has `--dry-run` (prints the request it would send, redacted) and requires
`--yes` or an interactive confirmation. The central skill's instructions tell Claude to ask the
user in chat before running a write with `--yes`. Writes that others can see are planned after
every read is working.

## Readiness from the knowledge base

| Dependency state | Command readiness |
|---|---|
| every endpoint `verified` twice | ready to build |
| some endpoint `hypothesis` or verified once | build after replay |
| some endpoint `unknown` in scope | open reverse-engineering step |
| signing or obfuscation caveat on a dependency | open step, needs js-reverse, built last |
