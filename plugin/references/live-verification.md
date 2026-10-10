# Live verification

A command is working when it ran against the live site in this session, returned exit 0, and its
stdout validated against the output schema in `plan.json`. Nothing else counts: not a green
offline suite, not a replay from the browser, not a run from an earlier session.

## Procedure

1. Confirm the session: `<slug> --env-file <root>/.env help` must report cookies present. If the
   first live call raises `SessionExpired`, stop and ask the user for fresh cookies.
2. State the budget before starting: the number of commands times their planned request counts.
   Ask before exceeding it.
3. Reads, one at a time, in build order:
   `uv run --project <root>/program <slug> --env-file <root>/.env <command> <smallest useful input>`.
   Validate stdout against the schema. For list commands, also run one page with a cursor to prove
   pagination advances and terminates.
4. Writes, only with the user's approval for that exact call and a value they chose. Run with
   `--dry-run` first, show the redacted request, then `--yes`. Prove the effect with a read rather
   than by repeating the write, and undo it if the user asked for a reversible test.
5. Stop at the first 429, challenge or checkpoint. Report it, do not retry.

## Evidence

Write one log per verification run to `<root>/var/logs/verify-<YYYY-MM-DD>-<HHMMSS>.json` holding,
per command: the command name, exit code, duration, request count, output item count, schema
result, and the error class if any. No values from the output, no cookie material.

Quote the log path and the per-command lines in the reply. For each command that passed, run
`kb.py verify --result pass` on every finding it depends on, so the knowledge base tally reflects
the program's own successful requests.

## Status words

- `verified live`: passed this procedure in this session.
- `built, not verified`: compiled and passed offline tests, not run live (state why).
- `blocked: <reason>`: could not be built, with the open reverse-engineering step named.
