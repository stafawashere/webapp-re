# Program architecture

A uv project at `<root>/program/`, Python 3.12 or later unless the plan names another language.
Created with `uv init --package --vcs none --name <slug>-client` (the app root already holds the repo), dependencies added with `uv add httpx`,
tests with `uv add --dev pytest`. Never pip.

## Layout

```
program/
   pyproject.toml           console script "<slug>" -> <package>.cli:main
   src/<package>/
      __init__.py           public names only: Client, models, errors
      session.py            Session: cookie jar adopted from .env or a session file, save and load
      transport.py          httpx.Client wrapper, browser-parity headers, redaction in logs
      pacing.py             Pacer: one in flight, minimum gap with jitter, stop-the-world on throttle
      classify.py           body-first classifier mapping responses to the error classes
      errors.py             SessionExpired, ChallengeRequired, RateLimited, ApiError, ContractBroken, NotPermitted, TransportError
      models.py             frozen dataclasses for every entity in the scope, parsed field by field
      endpoints.py          the only file with URL, path and operation-id literals, each citing its finding id
      capabilities/<group>.py   one function per command, typed in and typed out
      registry.py           command name -> function, input schema, output schema, kind, readiness
      cli.py                argparse over the registry, JSON to stdout, JSON errors to stderr, exit code per class
   tests/
      fixtures/             recorded response shapes with values replaced by synthetic ones
      test_parse.py         every model parsed from its fixture
      test_classify.py      every failure class from a fixture body
      test_registry.py      every planned command registered, schemas present
   scripts/check_provenance.py   the gate
```

## Rules that keep it honest

- **Typed at the boundary.** No public function returns a raw dict. Unknown or missing upstream
  fields fail loudly in the parser (`ContractBroken`) rather than defaulting silently, unless the
  scope recorded the field as partial coverage, in which case it is `Optional`.
- **Body-first classification** exactly as in
  `${CLAUDE_PLUGIN_ROOT}/references/failure-classification.md`. The classifier runs on every response before any parser
  sees it, and a 200 with an error envelope is an error.
- **Pacing lives in the program**, never in callers. Defaults from
  `${CLAUDE_PLUGIN_ROOT}/references/pacing-and-safety.md`. Expose the rate as configuration, with no hard floor, and
  never retry a challenge.
- **Session.** `Session.from_env(path)` reads cookie names listed in the scope from `.env`;
  `Session.save(path)` writes a file with mode 600. Cookie values never appear in logs, reprs, or
  exceptions; `repr(session)` shows names and lengths only.
- **Browser parity.** Send the headers ablation found required plus the ones a browser always
  sends (user agent copied from `.env`, accept, accept-language, origin, referer). Departures are
  configuration.
- **Endpoint literals in one file**, each with a `# finding: <id>` comment, which is what the
  provenance gate reads.
- **The CLI never takes secrets on argv.** `--env-file` points at the cookie file.
- **Exit codes**: 0 ok, 2 usage, 10 SessionExpired, 11 ChallengeRequired, 12 RateLimited,
  13 ApiError, 14 ContractBroken, 15 NotPermitted, 16 TransportError.

## Provenance gate

`scripts/check_provenance.py` loads `<root>/knowledge/endpoints/*.md`, keeps findings with
`status: verified` and `verify_count >= 2`, normalises their URLs to shapes (numeric and opaque
id segments become placeholders), scans `src/` for URL, path, host and operation-id literals, and
fails naming file and line for any literal without a backing finding. It runs a positive control
first: a fixture string with one known unbacked literal must produce exactly one violation, or
the gate exits 2 as unrunnable. Shape described in
`${CLAUDE_PLUGIN_ROOT}/references/provenance-gate.md`.

## Tests

Offline only, from fixtures whose values are synthetic. A live check is never part of the test
suite; it lives in `scripts/live_check.py` and is run by hand as in `live-verification.md`.
