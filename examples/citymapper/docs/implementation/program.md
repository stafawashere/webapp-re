# Program

The program built in stage 3: a uv package `citymapper_client` in `program/`, CLI `citymapper`.
The planned design is in [architecture/program-design.md](../architecture/program-design.md); this
page records what was built, how the parts depend on each other, and how it is checked. All paths
are relative to `apps/citymapper`.

## Call path

```
cli.py (argparse from schemas.json)
   -> registry.FUNCTIONS[command](context, arguments)
      -> capabilities/<area>.py
         -> context.py (region, place, time helpers)
            -> transport.py Request(endpoint, ...) -> Transport.send
               -> pacing.Pacer.turn (file lock, one request in flight)
               -> httpx -> classify.classify(status, content type, body, expect)
      <- models.py records (.as_dict())
   <- JSON on stdout, or JSON error on stderr with a class exit code
```

`cli.py` builds every subcommand from the input schema in `src/citymapper_client/schemas.json`
(underscored names become `--kebab` options, booleans become flags, arrays are comma split) and
adds `--env-file` and `--format json|table`. `schemas.json` is a copy of the command metadata in
[plan/plan.json](../../plan/plan.json), synced by `program/scripts/sync_schemas.py`; the plan stays
the source.

## Modules

| Module | Owns | Depends on |
|---|---|---|
| `errors.py` | `CitymapperError` and its subclasses with exit codes (table below), `as_dict()` | nothing |
| `config.py` | `Paths` (env file, cache, state, logs, pacer state, readiness file), `site_paths()` with the `CITYMAPPER_ROOT` override, user agent, cache ages | nothing |
| `pacing.py` | `Pacer`: file-locked state in `var/state/pacer.json`, 3 s gap plus 20 to 40% jitter, `halt()` for 900 s after a 429 or challenge | config |
| `session.py` | Cookie parsing, `.env` reading, `Session.from_env`, `save()` (mode 600, keeps only `sessionid`, `csrftoken`, `uid`, `uid_set`, `cm_region`, `_locale`), `describe()` prints names and lengths only | errors |
| `classify.py` | Body-first classification of a response into data or an error class | errors |
| `endpoints.py` | Every URL the program sends. `ORIGIN`, `TURNSTILE_HOST`, 35 `Endpoint` and 22 `PendingEndpoint` literals, each citing its KB finding | nothing |
| `transport.py` | `Request` (url, body text, `describe()` for dry runs) and `Transport` (headers, cookies only on `signed_in` or `sends_cookies` endpoints, `X-CSRFToken` when `csrf`, GET retries after 5 s and 10 s, halt on 429 or challenge, request log) | pacing, classify, session |
| `catalogue.py` | Region and city catalogue from `window.citymapper` in server-rendered HTML (7-day cache), city resolution, `RegionConfigs` from `/resource/region-info/{id}` (1-day cache) | transport, endpoints |
| `context.py` | `Context`: send, region, region config, timezone, bounding-box check, place resolution (coords, or search then `placeresolve` for Google results), `to_utc_iso` | catalogue, transport |
| `models.py` | `require`, `require_list`, `coords_of`, record dataclasses `Place`, `RouteRef`, `Leg`, `Journey`, `Status`, `LineSummary`, `NearbyElement`, `Departure` | errors |
| `capabilities/journeys.py` | plan, walk, cycle, cab, journey times, refresh, trip links, travel time, search, resolve, reverse geocode; retired ones raise `NotFound` | context, models |
| `capabilities/departures.py` | nearby, stop details, stop, departures (dispatch by `departure_api`), stop schedule | context, models |
| `capabilities/lines.py` | line status, disruptions, service message, line search, line, lines, vehicles, route paths | context, models |
| `capabilities/cities.py`, `misc.py` | cities, city, brands; map around, go links, news, page text, legal; retired weather and transit score | context |
| `capabilities/account.py`, `sharing.py`, `local.py` | session reads and writes, Pass, public writes, `adopt-session` | transport, session |
| `registry.py` | `FUNCTIONS` (56 commands plus `help`), schema loading, readiness lookup | all capabilities |

## Error classes and exit codes

| Exit | Class | Raised when |
|---|---|---|
| 2 | UsageError | Missing or wrong option, place outside the region's bounding box, write without `--yes` or `--dry-run` |
| 10 | SessionExpired | No session for a session command, or the site answers 401 or 403 on a signed-in endpoint |
| 11 | ChallengeRequired | A Cloudflare or other bot-check page in the body |
| 12 | RateLimited | HTTP 429 (the pacer then halts for 900 s) |
| 13 | ApiError | Other non-2xx answers |
| 14 | ContractBroken | A 2xx body missing a field the program needs |
| 15 | NotPermitted | The account may not do this |
| 16 | TransportError | Network failure after retries |
| 17 | NotFound | Unknown city, stop, line or place, a 404 slug, or a retired endpoint |

## Writes

`account.perform_write`: with `--dry-run` it returns `request.describe()` (method, URL, body, finding)
and a `confirm` digest (first 12 hex characters of sha256 over method, URL and body, with volatile
timestamps removed) and sends nothing. A send needs `--yes --confirm <digest>`; the program
recomputes the digest just before sending and refuses (exit 2, nothing sent) if the request
changed, for example because a text place resolved differently. Session writes need a session;
`vote-for-city` needs one too, because the site checks the csrftoken. Writes are never retried
and never follow a redirect (optimize F08, F18). `sharing.perform_write_public` is the same for public writes (share link, go link, city vote),
which need no session (share link and go link; the city vote moved to session writes in stage 5). `request.body` is `{}` for bodyless requests so every dry run matches its
output schema ([L13](../debugging/failures-and-lessons.md#l13-four-source-bugs-found-by-the-offline-tests)).

## Departures

`get_departures` reads `stopinfo`, takes `sharing_urls[0].departure_api` (`departures` for bus and
ferry, `metrodepartures`, `raildepartures`) and dispatches to one parser per feed. The bus parser
emits live rows from `live_departures_seconds`, otherwise timetabled rows from `next_departures`
with `time` set to the ISO string, otherwise one `no live times` advisory row. Rows sort live first,
then by `seconds_away`, then by `time` (`departure_order`). `add_favourite` uses the same
`departure_api` to tell a bus stop (`target_type` 1) from a station (2); lines are 3.

## Gates and checks

| Gate | Command (from `program/`) | Last line on 2026-10-10 |
|---|---|---|
| Offline tests | `uv run --offline pytest -q` | `502 passed in 1.12s` (after stage 5; 372 after stage 3) |
| Provenance | `uv run --offline python scripts/check_provenance.py` | `positive control: 3 of 3 planted defects caught`, `Endpoint 35, PendingEndpoint 22`, `provenance violations: 0` |
| Live check | `uv run python scripts/live_check.py [--only labels]` | full run `live check: 32 of 33 runs passed; 38 requests`; reruns `4 of 4` (twice) |

The provenance gate parses `endpoints.py` and fails when an `Endpoint` literal's finding is not
verified at least twice, or a `PendingEndpoint` literal's finding is missing or dead, or a URL
literal appears outside `endpoints.py` without a `provenance-ignore` reason. It plants three
defects in a copy first and must catch all three.

The live check (`scripts/live_check.py`) runs each read command once with fixed inputs across NYC,
London, Paris, Berlin, Tokyo and the SF Bay Area, validates the output against the command's output
schema with `scripts/mini_schema.py`, applies invariants (times in order, live departures first and
in order, every departure row carries seconds, a time or an advisory, bikes counted, all 115
regions present), and writes `var/state/readiness.json`. It never asserts live values.

Offline tests (`program/tests/`, written by a background agent on synthetic fixtures for an invented
`zz-portvale` region, never copied from captures): support, registry, classify, pacing, session,
transport, commands, writes and CLI. `tests/support.py` provides a fake transport keyed by finding
id, so a test fails if a command calls an endpoint it should not.

## Readiness

`var/state/readiness.json` holds one status per command. On 2026-10-10 after stage 3:
29 verified live, 3 built and awaiting approval (share-journey, create-go-link, vote-for-city),
2 local (help, adopt-session), 23 blocked: 12 need your session (list-saved-places,
list-favourites, pass-account, pass-session-time and the 8 round-trip writes), 5 need your session
then approval (sign-out and 4 Pass writes), 4 retired upstream (plan-vehicle-hire, get-weather,
get-transit-score, get-shared-eta), 2 need a public slug (open-trip-link, open-go-link).
`tools/engineer/render_skill.py` turns this into the status column of
`plugin/skills/citymapper/SKILL.md`.

## Changes from optimize run-2026-10-10-092702

Caches: stops (`var/cache/stops-<region>.json`), resolved text places (`places-<region>.json`),
the brand directory, and route status for 60 s, so `get-departures`, `plan-*` with text places,
`list-brands` and the status pair send fewer requests. httpx loads lazily (import 76 to 57 ms).
Transport: no automatic redirects; same-host read redirects are followed and logged per hop;
cross-host only without credential headers ([D20](../decisions/decisions.md#d20-cross-host-redirects-only-without-credentials)).
Every request log line carries `run`, `command` and `attempt`; `live_check.py` counts requests by
run id and honours `CITYMAPPER_ROOT` and `--root`, and downgrades a command to `failing live`
when it fails. A broken cache is refetched; shape drift exits 14 as JSON. Booleans accept
`--no-<flag>`, so `update-profile` sends only the fields passed. HH:MM more than 15 minutes in the
past means tomorrow. `--format table` shows each command's primary list. The provenance gate now
plants 8 source defects and 3 objects. Full list: [result.md](../../optimize/run-2026-10-10-092702/result.md).
