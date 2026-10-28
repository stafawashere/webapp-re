# Tests

Fixtures the pipeline's scripts are checked against. Every value in them is fake and planted on
purpose, and the example site is `app.example.test`.

| Fixture | For | Expected |
|---|---|---|
| `fixtures/scope-check/scope-good.json` | `check_scope.py` | 0 problems, exit 0 |
| `fixtures/scope-check/scope-bad.json` | `check_scope.py` | 3 problems: unknown endpoint, unknown pagination scheme, secret-looking value; exit 1 |
| `fixtures/plan-check/` | `check_plan.py` | 4 problems on command `Add_Item`; exit 1 |
| `fixtures/kb-cycle-home/` | `kb.py` | The tree one full `kb.py` cycle writes (init, new-run, record-finding, verify, record-pattern, close-run), kept as a reference. Its `var/` is gitignored, like in a real workspace |
| `fixtures/optimize-check/good/` | `optimize_run.py validate` | 2 findings (1 confirmed, 1 refuted), 0 problems, exit 0 |
| `fixtures/optimize-check/bad/` | `optimize_run.py validate` | 7 problems: run id not matching its directory, live spend over budget, duplicate id, unknown dimension, missing evidence, anchor not found, skipped outcome without a reason; exit 1 |
| `fixtures/optimize-check/applied/` | `optimize_run.py validate` | 2 findings (2 confirmed), one marked fixed whose anchor is gone, 0 problems, exit 0 |
| `fixtures/capture-site/` | `cdp_capture.py`, `capture-hook.js` | A page that fires a POST with a fake CSRF header and form token, both of which must come out redacted |
| `fixtures/menu-site/` | `menu/build_menu.py`, through `test_build_menu.py` | A site with a command added after its hints (`brand-new`), hints for a removed command and a removed field, a `--yes` input, an unbuilt write, and a purpose holding `</script>`; 22 tests, `OK`. The cache, sync, determinism, contract, output and server tests copy it to a temporary directory first |

## Running them

From the repository root, because the optimize fixtures name `target.py` by a path relative to it.
The scripts and tests are uv inline scripts, so `uv` is all they need. The capture test below
also needs a Chromium.

```bash
uv run --script tests/test_build_menu.py
uv run --script tests/test_upgrade_check.py
uv run --script plugin/scripts/check_scope.py tests/fixtures/scope-check/scope-good.json
uv run --script plugin/scripts/check_scope.py tests/fixtures/scope-check/scope-bad.json
uv run --script plugin/scripts/check_plan.py tests/fixtures/plan-check
uv run --script plugin/scripts/optimize_run.py validate tests/fixtures/optimize-check/good/run-2026-10-09-120000/findings.json
uv run --script plugin/scripts/optimize_run.py validate tests/fixtures/optimize-check/bad/run-2026-10-09-120001/findings.json
uv run --script plugin/scripts/optimize_run.py validate tests/fixtures/optimize-check/applied/run-2026-10-09-120002/findings.json
```

The capture test needs a Chromium listening for CDP on a throwaway profile, plus the fixture
server:

```bash
uv run python tests/fixtures/capture-site/serve.py tests/fixtures/capture-site/site
```

That serves on `127.0.0.1:8765` and answers POST like GET. This one is a manual check. Run
`cdp_capture.py` against `http://127.0.0.1:8765/` and check that the capture JSONL has the token values redacted.
`capture-hook-with-driver.js` is `capture-hook.js` with one extra line at the end that fires a
fetch and an XHR and dumps the records, for pasting into a page console.

## Not covered yet

The scope probe and the reverse fast path (`scope-probe.js`, `scope-paginate.js`,
`reverse-capture.js`, `reverse-ablate.js`, `reverse-export.js`, `walk_summary.py`,
`scope_query.py` and `replay.py`) have no fixtures here yet. They were checked by live runs on
GitHub and hn.algolia.com, and those captures hold account data, so they stay out of the repo.
