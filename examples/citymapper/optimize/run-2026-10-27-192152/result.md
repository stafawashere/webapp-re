# Optimize result, citymapper, run-2026-10-27-192152

## Before and after

| Metric | Before | After | Unit |
|---|---|---|---|
| tests | 0 | 0 | exit code |
| tests passed | 502 | 567 | tests |
| tests wall time | 2.28 | 173.35 | s |
| provenance gate | 0 | 0 | exit code |
| cli --help wall time, median | 711 | 1576 | ms |
| cli help command wall time, median | 197 | 494 | ms |
| import time of citymapper_client.cli | 82.7 | 757.9 | ms |
| check_scope | 0 | 0 | exit code |
| check_plan | 0 | 0 | exit code |
| site plugin check | 0 | 0 | exit code |
| claude plugin validate | 0 | 0 | exit code |

## Findings

| Id | Severity | Title | Outcome | Reason |
|---|---|---|---|---|
| F01 | high | --signatures splits on commas, but a journey signature is a JSON string full of commas | fixed |  |
| F02 | high | Site renderer still emits the pre-launcher skill, so the next engineer run reverts the plugin skill | fixed |  |
| F04 | medium | search-places and resolve-place feed no cache, and the skill's coords advice fails for Google results | fixed |  |
| F05 | medium | A write that times out is reported as a plain network error with no warning that it may have landed | fixed |  |
| F06 | medium | HTML where JSON was expected is ContractBroken, so a login page or a non-Cloudflare bot check is neither SessionExpired nor ChallengeRequired and never halts the pacer | fixed |  |
| F07 | medium | An OSError after the response (request log or cache write) escapes as a traceback, even after a write landed | fixed |  |
| F08 | medium | Any KeyError, TypeError, AttributeError or ValueError is reported as ContractBroken (exit 14), with no field name | fixed |  |
| F09 | medium | Path values are not URL-quoted, so an approved dry run can send a different endpoint than the one it shows | fixed |  |
| F10 | medium | Skill never says who runs adopt-session, so the agent may handle the raw Cookie header in chat or in its own command line | fixed |  |
| F11 | medium | Provenance gate path regex is a hardcoded prefix list and misses most unbacked literals | fixed |  |
| F12 | medium | live_check.py and auto_adopt_session.py call uv run without pinning UV_PROJECT_ENVIRONMENT | fixed |  |
| F13 | medium | Status.from_api turns a missing status into level 0, which means Good Service | not attempted |  |
| F14 | medium | Departures, saved places and favourites return empty lists when their list field disappears | not attempted |  |
| F16 | low | Region config (timezone, nearby modes) is refetched every 24 hours though it is static | fixed |  |
| F17 | low | to_utc_iso fetches region config even for offset-qualified ISO times | fixed |  |
| F18 | low | 40 second HTTP timeout multiplies across read retries | fixed |  |
| F19 | low | Session.save truncates .env in place and rewrites it without comments, blank lines or quotes | fixed |  |
| F20 | low | Option conflicts and bad times are checked only after the places have been resolved over the network | fixed |  |
| F21 | low | A leading newline or space before 'Cookie:' makes adopt-session store the wrong cookie names and report 'No sessionid cookie' | fixed |  |
| F22 | low | --limit is not validated: 0 is ignored and negative values slice from the end | fixed |  |
| F23 | low | Git-tracked site bundles embed third-party API keys and a Sentry DSN | fixed |  |
| F24 | low | Stale 'standing overnight grant' wording on eight account writes contradicts the skill's per-call approval rule | fixed |  |
| F25 | low | Legend implies a second approval channel (PENDING-APPROVALS.md) that the program never checks | fixed |  |
| F26 | low | Exit 15 NotPermitted is documented but never raised, and a 403 tells the user to re-adopt their session | fixed |  |
| F27 | low | Nothing guards schemas.json against drifting from plan/plan.json | fixed |  |
| F28 | low | Dead code: unused constant, helper, error class and endpoint constants | fixed |  |
| F29 | low | Site README says var/logs holds only the kb.py log, but the program writes its request log there | fixed |  |
| F30 | low | dataclasses (and inspect) dominate CLI import time | not attempted |  |
