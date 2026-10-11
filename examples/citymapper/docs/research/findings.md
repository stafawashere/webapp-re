# Findings

Stage 1 research results. The complete endpoint list with query keys, body fields and shapes is
[scope/scope.json](../../scope/scope.json); this page records what that list cannot say.

## Endpoint surface

FACT: 68 scope endpoints, 3 of them noise (`logevents`, `resourceproxy-images`, `static-img`).
Observed live: journeys, walk7, cycle, taxi, journeytimes, trip-meta, searchpost, nearby3, nearby2,
stopinfo, the three departures endpoints, routeinfo1, routeinfo2, routestatus, findtransport (URL
only), message, city-html, cities-html, news-html, resource-region-info, resource-brand-directory,
identity-user-data (403). Bundle only: refreshjourneys, gettrip, createtripurl, createshorturl,
getshorturl, eta, placeresolve, geocode, everythingmap, schedules, routepaths, vehiclelocations,
weather, transitscore, traveltime, blog, resources, walk1, vehiclehire, every identity endpoint, every
turnstile endpoint, city-vote.

Bundle inventory counts (subagent, INFERENCE): 61 methods registered on `CitymapperAPI` plus 7 direct
calls; 33 of the 61 have a caller in either bundle.

## Request conventions

- FACT: GETs carry `start`/`end` as `lat,lng` strings and `region_id`; flags are `1`; journeys add
  `status_format=html` (status text as HTML), line calls `status_format=rich`.
- FACT: times are ISO 8601 in UTC with milliseconds on the way in (`2026-10-10T14:40:00.000Z`) and
  ISO with the region's offset on the way out (`2026-10-10T20:08:00+02:00`).
- FACT: `searchpost` posts JSON under a form content type, with `Citymapper-Client: Web Search` and
  `Citymapper-Region`. Recorded as KB pattern `quirk-searchpost-form-json`.
- FACT: `journeytimes` posts `{"signatures": [...]}` where each signature is the 900-character JSON
  string from `journeys[].signature`. The name "signature" is the planner's journey descriptor, not
  a cryptographic signature.
- FACT: the wire carried no `X-CSRFToken`, no `Authorization`, no custom auth header on any public call.

## Regions and cities

FACT (from `window.citymapper.regions` in the `/nyc` HTML, saved to `research/regions.json`):

- 115 regions, all `region_is_launched` and `web_enabled`; 107 `api_enabled`. The 8 without API:
  `fr-nantes`, `fr-bordeaux`, `fr-toulouse`, `fr-strasbourg`, `fr-marseille`, `ch-ch`, `mc-monaco`,
  `at-vienna`. What `api_enabled: false` means for routing is UNRESOLVED.
- Each region entry is `[region, distance_km]`; the distance is from the requester (the order put
  New York first at 12,639 km, consistent with a Paris IP). Region fields: `region_id`, `region_name`,
  `region_name_aliases`, `region_slug`, `bounding_box`, `default_place`, `region_dude`,
  `region_growth_percent`, plus the flags above.
- 252 cities in `citiesInRegions`, keyed by city slug, each with `city_id`, `city_name`,
  `region_id`, `default_place`, `show_in_city_switcher` (20 are shown in the switcher).
- Region slugs are not always city names: `us-cleveland` is `ohio`, `us-westflorida` is `sarasota`,
  `ca-newbrunswick` is `dieppe`, `us-minneapolis` is `twincities`, `us-sf` is `sfbayarea`, `mx-df` is
  `df`, `pt-lisbon` is `lisboa`, `it-rome` is `roma`, `ae-ae` is `united-arab-emirates`.
- Region config fields from `window.citymapper.region` or `/resource/region-info/{id}`:
  `nearby_modes`, `offline_maps`, `timezone`, `core_brand_ids`, `default_cycle_brand_id`,
  `distance_units`, `clock`, `temperature_units`, `ondemand`, `feature_*` flags. NYC has 40 brands
  in `window.citymapper.brands`; London has 13 nearby modes, Paris 10.

## Live data observations (values change; recorded only to show shape)

- NYC routestatus at 08:31 EDT: 8 groupings; most subway lines at level 1 (skipping stations,
  reduced frequency), the 6 at level 2 (section closed).
- Times Sq-42 St metrodepartures: 4 sections; a grouping mixed live `time_seconds` entries with
  `scheduled_time` entries and an advisory `No current departures` row (`is_advisory_message: 1`).
  So departures are not uniformly live, and live and scheduled entries interleave.
- Grand Central raildepartures: 18 departures, each with `scheduled_time`, `expected_departure_time`,
  `time_seconds`, `is_live`, `platform_number` null.
- Bus stop `7-avw-44-st` (id `405297_1`): 3 services with `live_departures_seconds` lists.

## Account surface (bundle, INFERENCE)

Sign-in providers: e-mail magic link (`identity/magiclink/create`), Google GIS token and Facebook SDK
token (`identity/sessions` with `auth_provider`). Password and signup methods exist in the API layer
with no UI caller; no Apple sign-in. Signed-in data: saved places (list, create, update, delete;
`role` home or work), favourites (`target_type` 1 bus stop, 2 station, 3 line), saved journeys
(create and delete only), `update_user` (first_name, last_name, mobile, is_interested_in_pass). The
web delete-place call is broken in the client (`placeId` vs `place_id`). Turnstile (Pass payments)
needs `User-Device` and `Session-Id` headers.

## Things that are not what they look like

- "Turnstile" is Citymapper's Pass payment API, not Cloudflare Turnstile.
- "Signature" is a journey descriptor, not a signing scheme.
- `createtripurl` and `createshorturl` are GETs that create public links (writes).
- `/{region}/l/{alias}` line URLs from `routes[].url` redirect to `/{region}/{mode}/{alias}`.
- Bike docks look like stops in nearby results but have no detail page.

## Knowledge base state

`kb.py stats`: `findings: 65 (65 hypothesis)`; patterns `noise-logevents`, `noise-third-party`,
`technique-cdp-for-bodies`, `surface-embedded-region-config`, `quirk-searchpost-form-json`,
`quirk-departure-api-per-brand`, `quirk-line-url-redirect`. Ledger entry for
`run-2026-10-10-082844` in `knowledge/sessions.md`.

## Stage 3 findings (replays and live checks)

FACT, each from replays or the program's live check on 2026-10-10:

- Every public read endpoint in the plan answered from plain httpx with no cookies and no challenge:
  journeys, walk7, walk1, cycle, taxi, journeytimes, refreshjourneys, trip-meta, searchpost,
  placeresolve, geocode, nearby3, nearby2, stopinfo, departures (bus), metrodepartures,
  raildepartures, schedules, routeinfo1, routeinfo2, routestatus, routepaths, vehiclelocations,
  message, traveltime, everythingmap, blog, resources, region-info, brand-directory, the city and
  cities pages.
- Retired: `/api/7/vehiclehire` answers 404 `{"error": "This API is no longer supported"}`;
  `/api/1/eta`, `/api/1/weather`, `/api/1/transitscore` answer 404 with an HTML "Page Not Found".
  Two replays each, two regions. Findings dead.
- `gettrip` and `getshorturl` answer 404 for an unknown slug; no public slug was available to test a
  hit (pattern `quirk-slug-links-404`).
- London bus stops: `services[]` carry `live_departures_seconds` when live, otherwise
  `next_departures`, a list of ISO times with offset (observed `2026-10-10T14:09:07+01:00`).
- `stopinfo` stops have no `kind` field; stop type follows `sharing_urls[].departure_api`.
- `nearby2` answers 500 without `brand_ids`. `everythingmap` takes `size=small|large` only.
- `journeytimes` omitted `time` on one entry once; not reproduced in four probes.
- Google results from `searchpost` have no coords; `placeresolve?id=google:<id>` returns them.

## Knowledge base state after stage 3

`kb.py stats`: `findings: 65 (4 dead, 26 hypothesis, 35 verified)`; 9 patterns (adds
`quirk-journeytimes-missing-time`, `quirk-slug-links-404`). The 26 hypotheses are the identity, Pass,
share-link, slug and city-vote endpoints, which need your session or a slug. Ledger entry for
`run-2026-10-10-090401` with 152 requests.
