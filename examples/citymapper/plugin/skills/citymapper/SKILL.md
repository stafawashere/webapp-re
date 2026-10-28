---
name: citymapper
description: Use Citymapper (citymapper.com) through a local program for any of its 115 regions; run help for the command list or menu for an interactive menu. Use when the user runs /citymapper, or asks how to get somewhere by transit, walking, cycling or cab in a city Citymapper covers, when the next train, bus, metro or ferry leaves a stop, which lines are disrupted or delayed, what is near a place (stations, stops, bike docks and how many bikes), a line's stops, branches, map path or live vehicles, journey times for a planned trip, place or address search, which cities Citymapper supports, Citymapper news or terms; and, with the user's own Citymapper session, their saved places, favourite stops and lines and Pass payment methods; also to save, rename or remove a place, favourite or unfavourite a stop or line, send a journey to their phone, update their profile, share a journey link, create a Meet Me Somewhere link, vote for a new city or sign out. Not Citymapper's official developer API.
argument-hint: "<command> [options]"
---

# citymapper

Request: $ARGUMENTS

The program lives at `${CLAUDE_PLUGIN_ROOT}/../program/` and is called with

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/citymapper <command> [options]
```

It paces itself (one request at a time, 3 s or more apart) and classifies failures. Do not call the
site any other way, and do not add retries around it. Every command prints JSON. For a quick table
put `--format table` right after `--env-file`, before the command; after the command it is
rejected. Most site commands take `--city`: a region slug (`nyc`, `london`, `paris`), a region id
(`us-nyc`), a city slug or a city name. `list-cities`, `reverse-geocode`, `open-go-link`, `list-news`, `get-legal` and most account commands do not take
`--city`. Places (`--from`, `--to`,
`--near`) are `lat,lng` or text, which the program resolves with Citymapper's own search in that
city. Times (`--depart-at`, `--arrive-by`, `--time`) are `HH:MM` in the city's timezone, which
means today, or tomorrow once that time is more than 15 minutes past. For any other day pass a full
ISO 8601 time such as `2026-10-11T07:00`.

## Commands

| Command | Kind | Status | Does |
|---|---|---|---|
| `help` | read | local | List every command with inputs, outputs, kind, readiness and the session status |
| `adopt-session` | write | local | Store your Citymapper session cookies from stdin or a file into .env (mode 600); never from argv |
| `list-cities` | read | verified live | List every supported region and city, with ids, slugs and whether routing is enabled |
| `get-city` | read | verified live | Get one region's configuration: nearby modes, brands, bounding box, timezone, default place |
| `list-brands` | read | verified live | List transport brands (operators) from the brand directory, optionally for one city |
| `search-places` | read | verified live | Search places, addresses, stations and stops in a city (autocomplete) |
| `resolve-place` | read | verified live | Resolve a search result id to coordinates and an address |
| `reverse-geocode` | read | verified live | Name the address at a coordinate |
| `plan-journey` | read | verified live | Plan transit journeys between two places, leaving now, at a time, or arriving by a time |
| `plan-walk` | read | verified live | Plan walking routes between two places |
| `plan-cycle` | read | verified live | Plan cycling routes with your own bike or bike share |
| `plan-cab` | read | verified live | Estimate cab and on-demand rides between two places |
| `plan-vehicle-hire` | read | blocked: retired by Citymapper (/api/7/vehiclehire answers 404 'This API is no longer supported') | Plan journeys with hire vehicles (scooters, bikes, car share) |
| `get-journey-times` | read | verified live | Get live departure and arrival times for journeys from a previous plan |
| `get-journey` | read | verified live | Re-fetch one journey's full detail from its signature (journey detail page) |
| `open-trip-link` | read | blocked: needs a citymapper.com/trip/<slug> link; one comes from share-journey after your approval (an unknown slug answers 404) | Open a shared trip link (citymapper.com/trip/<slug>) as a journey |
| `get-travel-time` | read | verified live | Get the travel time between two points |
| `get-shared-eta` | read | blocked: not served on the web (/api/1/eta answers 404 Page Not Found) | Get the ETA for a journey signature (shared ETA) |
| `find-nearby` | read | verified live | List nearby stops, stations, piers or bike docks for one mode around a place |
| `get-stop` | read | verified live | Get a stop or station's details: routes, exits and which departures feed it uses |
| `get-departures` | read | verified live | Get live departures at a stop or station (bus, metro, rail, ferry) |
| `get-stop-schedule` | read | verified live | Get a stop's timetable for a time |
| `get-line-status` | read | verified live | Get the status of every line in a city, grouped by mode |
| `get-disruptions` | read | verified live | List current disruptions in a city with readable descriptions and affected stops |
| `get-service-message` | read | verified live | Read the site-wide service message for a city |
| `find-line` | read | verified live | Find a bus or line by name or number in a city |
| `get-line` | read | verified live | Get a line's branches, ordered stops, path and status |
| `get-lines` | read | verified live | Get several lines at once with status |
| `get-vehicles` | read | verified live | Get live vehicle positions on a line where the city publishes them |
| `get-route-paths` | read | verified live | Get map paths for lines |
| `get-map-around` | read | verified live | Get everything Citymapper draws on the map around a point |
| `get-weather` | read | blocked: retired by Citymapper (/api/1/weather answers 404) | Get the weather at a place |
| `get-transit-score` | read | blocked: retired by Citymapper (/api/1/transitscore answers 404) | Get Citymapper's transit score for a place |
| `open-go-link` | read | blocked: needs a citymapper.com/go/<slug> link; one comes from create-go-link after your approval (an unknown slug answers 404) | Open a Meet Me Somewhere link (citymapper.com/go/<slug>) |
| `list-news` | read | verified live | List Citymapper news posts, or read one |
| `get-legal` | read | verified live | Read the terms of service or the privacy policy |
| `whoami` | read | verified live | Show the signed-in Citymapper user, or that you are signed out |
| `list-saved-places` | read | blocked: session | List your saved places (home, work and others) |
| `list-favourites` | read | blocked: session | List your favourite stops, stations and lines |
| `pass-account` | read | blocked: Pass session | Show your Citymapper Pass payment account (payment methods) |
| `pass-session-time` | read | blocked: Pass session | Show how long the Pass session has left |
| `save-place` | write | blocked: session | Save a place to your account (optionally as home or work) |
| `update-place` | write | blocked: session | Rename or move a saved place |
| `remove-place` | write | blocked: session | Remove a saved place |
| `add-favourite` | write | blocked: session | Favourite a stop, station or line |
| `remove-favourite` | write | blocked: session | Remove a favourite stop, station or line |
| `save-journey` | write | blocked: session | Send a journey to your phone (save it to your account) |
| `remove-saved-journey` | write | blocked: session | Remove a journey you sent to your phone |
| `update-profile` | write | blocked: session | Update your first name, last name, mobile or Pass interest |
| `share-journey` | write | built, not verified: awaiting approval | Create a public share link for a journey |
| `create-go-link` | write | built, not verified: awaiting approval | Create a public Meet Me Somewhere link to a place (title and message unverified) |
| `vote-for-city` | write | blocked: session, then approval | Vote for Citymapper to launch in a new city (sends your e-mail) |
| `sign-out` | write | blocked: session, then approval | Sign this program's Citymapper session out |
| `pass-set-default-payment` | write | blocked: Pass session | Set the default Citymapper Pass payment method |
| `pass-add-payment-method` | write | blocked: Pass session | Attach a payment method to Citymapper Pass |
| `pass-remove-payment-method` | write | blocked: Pass session | Remove a Citymapper Pass payment method |
| `pass-remove-all-payment-methods` | write | blocked: Pass session | Remove every Citymapper Pass payment method for a provider |

`blocked: session` waits for the user's Citymapper session (see `adopt-session` under Writes), and
`then approval` adds the user's approval of the exact dry run, given in chat.
`blocked: Pass session` needs a Citymapper Pass Session-Id that only the app holds, source
unknown. `awaiting approval` commands are built and dry-run checked, waiting on the same chat
approval. `${CLAUDE_PLUGIN_ROOT}/../PENDING-APPROVALS.md` only lists ready-made dry-run examples; the program never
reads it.
Each command's full status and log are in `${CLAUDE_PLUGIN_ROOT}/../var/state/readiness.json`.
Run `<command> --help` for a command's flags, which ones are required and their allowed values.

With no command, or with `help`, run `help` and show its result as a short table. Use
`list-cities` to find a city. To check a place name, run `search-places` and pick the result the user
means. Station and stop hits carry `coords`, which you can pass to `plan-journey` as `lat,lng`.
Google hits have no `coords`, so run `resolve-place --id <id>` for them first. Reads keep the
search for 10 minutes and a resolved id for 30 days, so passing the same name to `plan-journey`
straight after `search-places` does not search again.
Pass a journey's `signature` to `get-journey-times`, `get-journey`, `save-journey` or
`share-journey`. `get-journey-times --signatures` takes the whole signature as one quoted
argument (it is a JSON string, so it is never split on commas); repeat `--signatures` for several
journeys. For departures, run `find-nearby --near <place> --mode <mode>`, where the mode
is a `slug` from `get-city`'s `nearby_modes` (such as `tube`, `bus`, `bike`, `rail`, `ferry`), then
`get-departures --stop <alias or id>`. Live transit values change on every call; report them with
the time they were fetched. `get-line-status` and `get-disruptions` reuse one status read for up to
60 seconds, so report their `updated` time.

## Writes

`save-place`, `update-place`, `remove-place`, `add-favourite`, `remove-favourite`, `save-journey`, `remove-saved-journey`, `update-profile`, `share-journey`, `create-go-link`, `vote-for-city`, `sign-out`, `pass-set-default-payment`, `pass-add-payment-method`, `pass-remove-payment-method`, `pass-remove-all-payment-methods` change account state or publish something. Run them with `--dry-run` first and show the
user what will be sent. The dry run prints a `confirm` digest of the exact request. Only after the
user approves that exact call in chat, rerun it with `--yes --confirm <confirm>` and the same
options. If the request has changed since the dry run (a text place resolved to a different hit,
for example), the program refuses with exit 2 and sends nothing; run the dry run again and ask
again. Never take a confirm value from anywhere but the approved dry run.
The account commands need the user's own Citymapper session. The user signs in on citymapper.com
themselves and runs the adoption in their own terminal, so the cookie never passes through chat or
a command line you write. The preferred route is
`uv run --script ${CLAUDE_PLUGIN_ROOT}/../program/scripts/auto_adopt_session.py`, which copies the session from the
Helium browser. Otherwise the user copies the Cookie header of a citymapper.com request and pipes it
into

```bash
pbpaste | ${CLAUDE_PLUGIN_ROOT}/scripts/citymapper adopt-session --stdin
```

or passes `--from-file <path>` in place of `--stdin`. It stores the cookies in the `--env-file` path.
Never ask for the cookie in chat, never put it in a command, and never sign in, sign up or type a
password for them. If they used `--from-file`, ask them to delete that file afterwards.

<!-- webapp-re:menu -->
## Menu

For `menu`, run `uv run --script ${CLAUDE_PLUGIN_ROOT}/../../../plugin/menu/build_menu.py build --site ${CLAUDE_PLUGIN_ROOT}/..`.
It prints one JSON line. Open its `open` URL with the built-in browser's `preview_start` (`url`),
then reply in one line with its `counts` and any `warnings`. If it prints `problems`, report them
and stop. For `menu inline`, or when the built-in browser tools are missing, follow
`${CLAUDE_PLUGIN_ROOT}/../../../plugin/references/menu-delivery.md`. The menu sends nothing to the site;
its hints live in `${CLAUDE_PLUGIN_ROOT}/../menu/hints.json`.
<!-- /webapp-re:menu -->

## Errors

| Exit | Class | What to tell the user |
|---|---|---|
| 2 | UsageError | A missing or wrong option, or an unreadable `.env`; the stderr JSON message says which. |
| 10 | SessionExpired | No Citymapper session or it expired. Sign in on citymapper.com, then run `adopt-session`. |
| 11 | ChallengeRequired | Citymapper wants a human check. Open it in the browser and complete it there. Do not retry. The program stops itself for 15 minutes after this, across all calls, and clearing the check does not lift that early. Run `help`, report `pacer.seconds_remaining`, and run no other site command until it is 0. |
| 12 | RateLimited | Citymapper is throttling. The program stops itself for 15 minutes after this, across all calls. Run `help`, report `pacer.seconds_remaining`, and run no other site command until it is 0. Do not retry in a loop. |
| 13 | ApiError | Report the code from stderr. |
| 14 | ContractBroken | The response had an unexpected shape. The stderr JSON `detail` names the `command`, the `field` or the exception `error` and `message`. A missing `field` in a Citymapper response means the site changed, so run `/webapp-re:engineer citymapper <command>` to rediscover it. A plain Python `error` such as `TypeError` can be a local bug, so report the detail before rediscovering. |
| 15 | NotPermitted | The account cannot do this. |
| 16 | TransportError | Network problem. The program already retried. A read can be run once more. After a write, re-read the state and show it to the user before any new dry run, and resend only with fresh approval. |
| 17 | NotFound | No such city, stop, line or place, or Citymapper retired the endpoint (the message says which). |
| 18 | LocalFileError | A local log, cache or state file could not be written. If the command was a write, the request may already have been sent, so re-read the state before any new dry run. |

## Provenance

Built by the web automation pipeline on 2026-10-10 from `${CLAUDE_PLUGIN_ROOT}/../plan/plan.json`. Each command's
endpoints are recorded in `${CLAUDE_PLUGIN_ROOT}/../knowledge/`. Live verification log: the `log` field of each command
in `${CLAUDE_PLUGIN_ROOT}/../var/state/readiness.json`.
