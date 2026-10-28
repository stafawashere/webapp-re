# citymapper-client

Local client for the requests the citymapper.com website makes, used by the `/citymapper` skill.

```bash
export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
uv run --frozen --project . citymapper help
uv run --frozen --project . citymapper plan-journey --city london --from "51.503324,-0.119543" --to "King's Cross St Pancras" --arrive-by 19:00
uv run --frozen --project . citymapper get-departures --city nyc --stop times-sq-42-st
```

The `UV_PROJECT_ENVIRONMENT` export keeps uv on this program's own venv when the shell exports another project's.

Every command prints JSON (`--format table` for a table) and exits with a class-specific code on
failure. Public commands need no session. Account commands read cookies from the site root `.env`,
written by `adopt-session` from a Cookie header you copy from your own signed-in browser.

| Path | Holds |
|---|---|
| `src/citymapper_client/endpoints.py` | Every URL the program sends, each citing its knowledge base finding |
| `src/citymapper_client/capabilities/` | One function per command |
| `src/citymapper_client/schemas.json` | Command metadata and schemas, synced from `plan/plan.json` by `scripts/sync_schemas.py` |
| `scripts/check_provenance.py` | The provenance gate |
| `scripts/live_check.py` | Live verification against citymapper.com, writes `var/state/readiness.json` |
| `tests/` | Offline tests on synthetic fixtures |

Gates:

```bash
export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
uv run --offline pytest -q
uv run --offline python scripts/check_provenance.py
```
