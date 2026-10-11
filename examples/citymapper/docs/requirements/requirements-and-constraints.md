# Requirements and constraints

From your overnight brief of 2026-10-10. The brief is the authority; this page restates it so the
documents that cite it have one anchor.

## Goal

The Citymapper web app (https://citymapper.com/, slug `citymapper`) is fully engineered with the
fullest possible set of capabilities, the engineering is optimized, and the `/citymapper` menu shows
every capability as built and verified, or as built and waiting for approval, or as blocked with
the reason and the evidence.

Pipeline, in order, each gated on the previous stage's exit checks and followed by a doc-archive
pass: scope, plan, engineer (every planned command), optimize, optimize `--apply <run-id>`,
integrate-menu and display of `/citymapper menu`.

## Scope requirements for Citymapper

| Requirement | Where it is met in stage 1 |
|---|---|
| Cover every city; city is an input to every command | 115 regions and 252 cities from the page HTML, [findings](../research/findings.md#regions-and-cities); every endpoint takes `region_id` |
| Journey planning: from and to as addresses, places or coordinates; depart or arrive times; modes and preferences | `journeys`, `walk7`, `cycle`, `taxi`, `journeytimes`, [feature flows](../architecture/feature-flows.md#journey-planning) |
| Place and address search and autocomplete | `searchpost`, `placeresolve`, `geocode` |
| Nearby stops and stations | `nearby3`, `nearby2` |
| Live departures and arrivals | `departures-bus`, `departures-metro`, `departures-rail` (arrivals at the end of a journey come from journey legs) |
| Line and route pages with stops and service status | `routeinfo1`, `routeinfo2`, `findtransport` |
| Disruptions and alerts | `routestatus` disruptions, line `status` objects, `message` |
| Maps data | journey leg `shape`, pattern `path`, `routepaths`, `everythingmap`, `vehiclelocations` |
| City coverage | `city-html`, `cities-html`, `resource-region-info`, `resource-brand-directory` |
| Parameters, response shape, pagination or time-window per call | `scope/scope.json` endpoints and pagination schemes |
| Whether a signed-in account exists and what it adds | Yes: saved places, favourites, saved journeys, profile fields; Club and Pass are app-only paid features ([risks](../knowledge/risks-and-open-questions.md#account)) |
| Use only the website's own requests, never the official developer API | Followed; no developer key requested or used |
| Record signing, embedded tokens, rate limits, geographic restrictions, app-only features with evidence | `scope.json` caveats |

## Standing decisions that bind later stages

- Plan: every capability is in scope, reads and writes. JSON output by default. Build order: reads,
  then writes, then anything blocked on signing or obfuscation; within a tier journey planning, live
  departures, disruptions, then the rest.
- Request budgets may be exceeded, but never faster than
  `plugin/references/pacing-and-safety.md` (one request in flight, 3 s or more
  between requests to an origin with 20 to 40 percent jitter). No polling loops. Any 429, captcha,
  bot check or block stops that series.
- Stage 4 skips its ask gate; stage 5 applies every confirmed and plausible finding.
- Live account writes only when the program implements an exact, free inverse and the account is
  read before and after; never subscriptions, payments, anything public or shared, feedback or
  messages, or deletes without an inverse. Those are built, tested offline and with `--dry-run`,
  and listed in `PENDING-APPROVALS.md`.
- Hard limits: never type a password, create an account, solve or bypass a captcha, buy anything,
  or change account security.

## Working rules

Background anything over a minute; never loosen a checker; check schemas and invariants of live
transit data, never exact values; change strategy after two failed approaches; keep
a run log current and write a report at the end.

## Workspace limits

Work only in `apps/citymapper`, the skill's own files and `plugin/skills/citymapper`. Other site
folders (`commonapp`, `appybara`, `collegevine`, `niche`, `lumisource`, `collegecalcai`) are worked
examples of layout only. In the browser, open your own tab and leave every other tab alone.
