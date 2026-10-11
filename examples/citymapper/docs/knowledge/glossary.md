# Glossary

| Term | Meaning here |
|---|---|
| region | Citymapper's unit of coverage, id like `us-nyc`, slug like `nyc`; every API call takes `region_id` |
| city | A named place inside a region (252), keyed by city slug; the API never takes a city id |
| brand | A transport operator or network id (`NewYorkSubway`, `CitiBike`, `MNR`); brands pick the departures API |
| nearby mode | A region's mode tile (`us-nyc-subway`), with the brand ids and kinds used by nearby searches |
| alias | URL-friendly stop or line id (`times-sq-42-st`, `subway-6`); `stopinfo` and `routeinfo` accept it |
| live_code | Internal stop id used by departures (`SubwayTimesSq42St`) |
| pattern | A line branch or direction with ordered stop points and a path |
| journey signature | The JSON journey descriptor in `journeys[].signature`, sent to `journeytimes` and `refreshjourneys`; not a cryptographic signature |
| `status_format` | `html` on journey calls, `rich` on line calls; controls how status text is formatted |
| level | Status severity on lines and disruptions: 0 good, 1 minor, 2 severe (as observed) |
| turnstile | Citymapper's Pass payment API host, not Cloudflare Turnstile |
| go link | A Meet Me Somewhere short link (`/go/{slug}`) |
| CDP Brave | The separate Brave instance on port 9222 with profile `~/.webapp-re-profile`, used for captures |
| observed | Seen live on 2026-10-10; the opposite is bundle-only INFERENCE |
| `departure_api` | The feed a stop's departures come from (`departures`, `metrodepartures`, `raildepartures`), in `stopinfo` `sharing_urls[]` |
| `Endpoint` / `PendingEndpoint` | Program URL literals: verified twice, or recorded but not verifiable yet ([D11](../decisions/decisions.md#d11-two-endpoint-classes-and-a-provenance-gate)) |
| readiness | Per-command status in `var/state/readiness.json`: verified live, built awaiting approval, local, or blocked with a reason |
| live policy | Plan field: `public` (no session), `session` (your session), `local` (no request) |
| dry run | `--dry-run` on a write: prints method, URL, body and finding; sends nothing |
| timetabled row | A departure with `is_live` false and a scheduled `time`, from `next_departures` |

