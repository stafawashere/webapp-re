# Citymapper plan

Generated 2026-10-10 from scope/scope.json (2026-10-10). Program `program/` (package `citymapper_client`), CLI `citymapper`, central skill `/citymapper`.

## Defaults

- Output: JSON on stdout by default, `--format table` for people; errors as JSON on stderr with a class and an exit code.
- City: every command takes `--city` (slug, region id, city slug or name), resolved from the cached catalogue.
- Pacing: one request in flight, 3 s minimum gap per origin with 20 to 40 percent jitter, no automatic retry except transport errors (2, backoff from 5 s), stop on 429 or challenge.
- Session: optional; cookies (sessionid, csrftoken, uid) adopted from your browser into <root>/.env by adopt-session; public commands send no session.
- Writes: `--dry-run` prints the exact request and its `confirm` digest; `--yes --confirm <digest>` is required to send, and a request that differs from the approved dry run is refused. Round-trip writes have an implemented inverse; approval writes go to PENDING-APPROVALS.md.

## Commands

| Command | Kind | Tier | Live policy | Readiness | Endpoints (state) | Requests | Purpose |
|---|---|---|---|---|---|---|---|
| help | read | base | local | local |  | 0 | List every command with inputs, outputs, kind, readiness and the session status |
| adopt-session | write | base | local | local |  | 0 | Store your Citymapper session cookies from stdin or a file into .env (mode 600); never from argv |
| list-cities | read | base | public | verified live | cities-html (verified), city-html (verified) | 1 | List every supported region and city, with ids, slugs and whether routing is enabled |
| get-city | read | base | public | verified live | resource-region-info (verified), city-html (verified) | 1 | Get one region's configuration: nearby modes, brands, bounding box, timezone, default place |
| list-brands | read | rest | public | verified live | resource-brand-directory (verified) | 1 | List transport brands (operators) from the brand directory, optionally for one city |
| search-places | read | journey | public | verified live | searchpost (verified) | 1 | Search places, addresses, stations and stops in a city (autocomplete) |
| resolve-place | read | journey | public | verified live | placeresolve (verified) | 1 | Resolve a search result id to coordinates and an address |
| reverse-geocode | read | journey | public | verified live | geocode (verified) | 1 | Name the address at a coordinate |
| plan-journey | read | journey | public | verified live | journeys (verified), searchpost (verified) | 1 | Plan transit journeys between two places, leaving now, at a time, or arriving by a time |
| plan-walk | read | journey | public | verified live | walk7 (verified), walk1 (verified) | 1 | Plan walking routes between two places |
| plan-cycle | read | journey | public | verified live | cycle (verified) | 1 | Plan cycling routes with your own bike or bike share |
| plan-cab | read | journey | public | verified live | taxi (verified) | 1 | Estimate cab and on-demand rides between two places |
| plan-vehicle-hire | read | journey | public | blocked: retired by Citymapper (/api/7/vehiclehire answers 404 'This API is no longer supported') | vehiclehire (dead) | 1 | Plan journeys with hire vehicles (scooters, bikes, car share) |
| get-journey-times | read | journey | public | verified live | journeytimes (verified) | 1 | Get live departure and arrival times for journeys from a previous plan |
| get-journey | read | journey | public | verified live | refreshjourneys (verified), trip-meta (verified) | 1 | Re-fetch one journey's full detail from its signature (journey detail page) |
| open-trip-link | read | journey | public | blocked: needs a citymapper.com/trip/<slug> link; one comes from share-journey after your approval (an unknown slug answers 404) | gettrip (hypothesis), refreshjourneys (verified) | 2 | Open a shared trip link (citymapper.com/trip/<slug>) as a journey |
| get-travel-time | read | journey | public | verified live | traveltime (verified) | 1 | Get the travel time between two points |
| get-shared-eta | read | journey | public | blocked: not served on the web (/api/1/eta answers 404 Page Not Found) | eta (dead) | 1 | Get the ETA for a journey signature (shared ETA) |
| find-nearby | read | departures | public | verified live | nearby3 (verified), nearby2 (verified) | 1 | List nearby stops, stations, piers or bike docks for one mode around a place |
| get-stop | read | departures | public | verified live | stopinfo (verified) | 1 | Get a stop or station's details: routes, exits and which departures feed it uses |
| get-departures | read | departures | public | verified live | stopinfo (verified), departures-bus (verified), departures-metro (verified), departures-rail (verified) | 2 | Get live departures at a stop or station (bus, metro, rail, ferry) |
| get-stop-schedule | read | departures | public | verified live | schedules (verified) | 1 | Get a stop's timetable for a time |
| get-line-status | read | disruptions | public | verified live | routestatus (verified) | 1 | Get the status of every line in a city, grouped by mode |
| get-disruptions | read | disruptions | public | verified live | routestatus (verified), routeinfo2 (verified) | 1 | List current disruptions in a city with readable descriptions and affected stops |
| get-service-message | read | disruptions | public | verified live | message (verified) | 1 | Read the site-wide service message for a city |
| find-line | read | rest | public | verified live | findtransport (verified) | 1 | Find a bus or line by name or number in a city |
| get-line | read | rest | public | verified live | routeinfo1 (verified) | 1 | Get a line's branches, ordered stops, path and status |
| get-lines | read | rest | public | verified live | routeinfo2 (verified) | 1 | Get several lines at once with status |
| get-vehicles | read | rest | public | verified live | vehiclelocations (verified) | 1 | Get live vehicle positions on a line where the city publishes them |
| get-route-paths | read | rest | public | verified live | routepaths (verified) | 1 | Get map paths for lines |
| get-map-around | read | rest | public | verified live | everythingmap (verified) | 1 | Get everything Citymapper draws on the map around a point |
| get-weather | read | rest | public | blocked: retired by Citymapper (/api/1/weather answers 404) | weather (dead) | 1 | Get the weather at a place |
| get-transit-score | read | rest | public | blocked: retired by Citymapper (/api/1/transitscore answers 404) | transitscore (dead) | 1 | Get Citymapper's transit score for a place |
| open-go-link | read | rest | public | blocked: needs a citymapper.com/go/<slug> link; one comes from create-go-link after your approval (an unknown slug answers 404) | getshorturl (hypothesis) | 1 | Open a Meet Me Somewhere link (citymapper.com/go/<slug>) |
| list-news | read | rest | public | verified live | news-html (verified), blog (verified) | 1 | List Citymapper news posts, or read one |
| get-legal | read | rest | public | verified live | resources (verified) | 1 | Read the terms of service or the privacy policy |
| whoami | read | account | session | verified live | identity-user-data (verified) | 1 | Show the signed-in Citymapper user, or that you are signed out |
| list-saved-places | read | account | session | needs session: not yet verified live | identity-places-list (hypothesis) | 1 | List your saved places (home, work and others) |
| list-favourites | read | account | session | needs session: not yet verified live | identity-favorites-list (hypothesis) | 1 | List your favourite stops, stations and lines |
| pass-account | read | account | session | blocked: needs a Citymapper Pass session from the app (Session-Id source unknown) | turnstile-userinfo (hypothesis) | 1 | Show your Citymapper Pass payment account (payment methods) |
| pass-session-time | read | account | session | blocked: needs a Citymapper Pass session from the app (Session-Id source unknown) | turnstile-sessionttl (hypothesis) | 1 | Show how long the Pass session has left |
| save-place | write | account-writes | session | needs session: round trip with inverse ready, dry run checked | identity-places-create (hypothesis), identity-places-list (hypothesis) | 2 | Save a place to your account (optionally as home or work) |
| update-place | write | account-writes | session | needs session: round trip with inverse ready, dry run checked | identity-places-update (hypothesis), identity-places-list (hypothesis) | 2 | Rename or move a saved place |
| remove-place | write | account-writes | session | needs session: round trip with inverse ready, dry run checked | identity-places-delete (hypothesis), identity-places-list (hypothesis) | 2 | Remove a saved place |
| add-favourite | write | account-writes | session | needs session: round trip with inverse ready, dry run checked | identity-favorites-create (hypothesis), identity-favorites-list (hypothesis) | 2 | Favourite a stop, station or line |
| remove-favourite | write | account-writes | session | needs session: round trip with inverse ready, dry run checked | identity-favorites-delete (hypothesis), identity-favorites-list (hypothesis) | 2 | Remove a favourite stop, station or line |
| save-journey | write | account-writes | session | needs session: round trip with inverse ready, dry run checked | identity-save-journey (hypothesis) | 1 | Send a journey to your phone (save it to your account) |
| remove-saved-journey | write | account-writes | session | needs session: round trip with inverse ready, dry run checked | identity-delete-journey (hypothesis) | 1 | Remove a journey you sent to your phone |
| update-profile | write | account-writes | session | needs session: round trip with inverse ready, dry run checked | identity-update-user (hypothesis), identity-user-data (verified) | 2 | Update your first name, last name, mobile or Pass interest |
| share-journey | write | approval | public | built, awaiting approval (dry run checked; PENDING-APPROVALS.md) | createtripurl (hypothesis) | 1 | Create a public share link for a journey |
| create-go-link | write | approval | public | built, awaiting approval (dry run checked; PENDING-APPROVALS.md) | createshorturl (hypothesis) | 1 | Create a public Meet Me Somewhere link to a place (title and message unverified) |
| vote-for-city | write | approval | session | needs session: then your approval (dry run checked; PENDING-APPROVALS.md) | city-vote (hypothesis) | 1 | Vote for Citymapper to launch in a new city (sends your e-mail) |
| sign-out | write | approval | session | needs session: then your approval (dry run checked; PENDING-APPROVALS.md) | identity-sessions-delete (hypothesis) | 1 | Sign this program's Citymapper session out |
| pass-set-default-payment | write | approval | session | blocked: needs a Citymapper Pass session from the app (Session-Id source unknown); dry run checked; PENDING-APPROVALS.md | turnstile-setdefaultpaymentmethod (hypothesis) | 1 | Set the default Citymapper Pass payment method |
| pass-add-payment-method | write | approval | session | blocked: needs a Citymapper Pass session from the app (Session-Id source unknown); dry run checked; PENDING-APPROVALS.md | turnstile-addpaymentmethod (hypothesis) | 1 | Attach a payment method to Citymapper Pass |
| pass-remove-payment-method | write | approval | session | blocked: needs a Citymapper Pass session from the app (Session-Id source unknown); dry run checked; PENDING-APPROVALS.md | turnstile-deletepaymentmethod (hypothesis) | 1 | Remove a Citymapper Pass payment method |
| pass-remove-all-payment-methods | write | approval | session | blocked: needs a Citymapper Pass session from the app (Session-Id source unknown); dry run checked; PENDING-APPROVALS.md | turnstile-deleteallpaymentmethods (hypothesis) | 1 | Remove every Citymapper Pass payment method for a provider |

## Build order

| Step | Do | Commands | Exit check |
|---|---|---|---|
| 1 | transport, pacer, classifier, session store, city catalogue and resolver | help, adopt-session, list-cities, get-city | help lists every command; list-cities returns 115 regions live; get-city returns nearby_modes for nyc and london |
| 2 | tier 1 reads: journey planning, search and journey times | search-places, resolve-place, reverse-geocode, plan-journey, plan-walk, plan-cycle, plan-cab, plan-vehicle-hire, get-journey-times, get-journey, open-trip-link, get-travel-time, get-shared-eta | plan-journey live in at least 3 cities (now, depart-at, arrive-by) with times in order and legs typed; search-places live |
| 3 | tier 2 reads: nearby, stops and live departures for bus, metro and rail | find-nearby, get-stop, get-departures, get-stop-schedule | get-departures live for a bus stop, a metro station and a rail station; departures typed, seconds non-negative |
| 4 | tier 3 reads: line status, disruptions, service message | get-line-status, get-disruptions, get-service-message | get-disruptions live in nyc and london with placeholders filled |
| 5 | remaining public reads: lines, maps, weather, news, legal, brands | list-brands, find-line, get-line, get-lines, get-vehicles, get-route-paths, get-map-around, get-weather, get-transit-score, open-go-link, list-news, get-legal | each command live once and its schema checked; bundle-only endpoints that no longer answer are recorded as blocked with the response |
| 6 | account reads, blocked until you sign in | whoami, list-saved-places, list-favourites, pass-account, pass-session-time | whoami signed-out path live; the rest built, offline tested, blocked on session |
| 7 | round-trip writes with exact inverses | save-place, update-place, remove-place, add-favourite, remove-favourite, save-journey, remove-saved-journey, update-profile | dry-run and offline tests; live round trip only with a session |
| 8 | approval writes: public links, city vote, sign-out, Pass payments | share-journey, create-go-link, vote-for-city, sign-out, pass-set-default-payment, pass-add-payment-method, pass-remove-payment-method, pass-remove-all-payment-methods | dry-run prints the exact request; PENDING-APPROVALS.md lists each |

## Not planned

| Capability | Reason |
|---|---|
| cap-sign-in | Signing in or up (magic link, Google or Facebook) can create an account and grants OAuth; the brief's hard limits forbid it. You sign in yourself, then adopt-session stores the cookie. |
| cap-password-reset | Password reset and sign-up confirmation are account-security e-mail flows; the hard limits forbid changing account security, and the web has no password sign-in. |
| cap-telemetry | Analytics (POST /api/2/logevents) is noise; the program never sends it. |

## Open reverse-engineering steps

| Command | Step | Budget |
|---|---|---|
| open-trip-link | observe gettrip live for the first time: needs a real trip slug; one comes from an approved share-journey, otherwise unverifiable | 2 |
| open-go-link | observe getshorturl live for the first time: needs a real go slug; one comes from an approved create-go-link | 2 |
| list-saved-places | replay identity-places-list twice and record two kb verify passes | 2 |
| list-favourites | replay identity-favorites-list twice and record two kb verify passes | 2 |
| pass-account | observe turnstile-userinfo live for the first time: needs a Pass session id from the app | 2 |
| pass-session-time | observe turnstile-sessionttl live for the first time: needs a Pass session id from the app | 2 |
| save-place | observe identity-places-create live for the first time: body shape and returned place_id | 2 |
| update-place | observe identity-places-update live for the first time: PUT body | 2 |
| remove-place | observe identity-places-delete live for the first time: status of a DELETE | 2 |
| add-favourite | observe identity-favorites-create live for the first time: body {target_type, target_id, region_id} | 2 |
| remove-favourite | observe identity-favorites-delete live for the first time: status of a DELETE | 2 |
| save-journey | observe identity-save-journey live for the first time: document_data shape and returned document_id | 2 |
| remove-saved-journey | observe identity-delete-journey live for the first time: status of a DELETE | 2 |
| update-profile | observe identity-update-user live for the first time: fields echoed back | 2 |
| share-journey | observe createtripurl live for the first time: only after your approval | 2 |
| create-go-link | observe createshorturl live for the first time: only after your approval | 2 |
| vote-for-city | observe city-vote live for the first time: only after your approval; needs the csrftoken cookie | 2 |
| sign-out | observe identity-sessions-delete live for the first time: only after your approval | 2 |
| pass-set-default-payment | observe turnstile-setdefaultpaymentmethod live for the first time: blocked: Pass session id is app-only | 2 |
| pass-add-payment-method | observe turnstile-addpaymentmethod live for the first time: blocked: Pass session id is app-only | 2 |
| pass-remove-payment-method | observe turnstile-deletepaymentmethod live for the first time: blocked: Pass session id is app-only | 2 |
| pass-remove-all-payment-methods | observe turnstile-deleteallpaymentmethods live for the first time: blocked: Pass session id is app-only | 2 |

## Risks

- You are signed out of citymapper.com; 19 session commands stay blocked until you sign in yourself and run adopt-session (whoami still answers signed out).
- Citymapper Pass and Club are paid and app-only; the six pass-* commands are blocked even with a web session.
- 15 endpoints were read from the bundle and never observed; some may be retired upstream (each is replayed once in engineer).
- Live transit values change every request; checks are on schemas and invariants only.
- Cloudflare fronts the site; unknown rate thresholds; the pacer stops the client on any 429 or challenge.
- City pages are 2 to 15 MB of HTML; the catalogue must be cached, never fetched per command.
