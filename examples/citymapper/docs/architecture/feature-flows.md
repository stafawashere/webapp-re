# Feature flows

Each feature from the user's action to the request and the fields that answer it. Endpoint ids are
the ids in [scope/scope.json](../../scope/scope.json) and in `knowledge/endpoints/`. "Observed" means
seen live on 2026-10-10; everything else is from the bundle inventory and is INFERENCE until stage 3
replays it.

## Journey planning

User action: type a start and an end (or click the map), pick Now, Arrive or Leave, press GO. The
page URL becomes `/directions?startcoord=lat,lng&endcoord=lat,lng&startname=&endname=&startaddress=`
plus `arrival_time=` or `departure_time=` (ISO 8601 UTC, for example `2026-10-10T14:40:00.000Z`).

Requests (observed in NYC, London and Paris), all GET with the same query:
`start=lat,lng&end=lat,lng&sname=&ename=&saddr=&region_id=&include_stepfree=1&include_via_microtransit=1&status_format=html`
plus `departure_time` or `arrival_time` when set.

| Endpoint | Returns |
|---|---|
| `journeys` `/api/7/journeys` | `sections[]` (`SUGGESTED` and others, each with journey indexes), `journeys[]` with `legs[]`, `duration_seconds`, `walk_seconds`, `distance_meters`, `calories`, `signature`, `journey_equivalence_hash`, `formatted_price`, `price_amount`, `currency_code`, `step_free`; `shared.station_exits`; `routing_request_id`; `log` with `Time Mode` (`Nowish`, `Leave`, arrive) and `Minutes Ahead Planned` |
| `walk7` `/api/7/walk?limit=2` | two walking profiles with `profile_id` (`fast`, ...), duration, distance, calories |
| `cycle` `/api/6/cycle` | `journey_kind` `cycle_personal` or `cycle_hire`, `profile_id` (`cyclequiet`, regular, fast), price and `representative_brand_id` for bike share; `shared.cycle_docks` |
| `taxi` `/api/2/taxi` | `routes[]` (mode taxi, `duration_seconds`, `length_meters`), `on_demand_model.categories[]` |

A transit leg holds `mode`, `routes[]` (id, brand_id, display_name, colors, `live_request_types`),
`stops[]` (id, name, coords, `duration_seconds_to_here`), `shape[[lat,lng]]`, `frequency`,
`departure_time`, `arrival_time` (ISO with the region's offset), `pattern_ids`, `boarding_info`.
Observed: a Paris `departure_time=2026-10-10T18:00:00.000Z` request answered `Time Mode: Leave`,
`Minutes Ahead Planned: 318`, 12 journeys, first transit leg departing `2026-10-10T20:08:00+02:00`.

Live times: `POST /api/1/journeytimes?region_id=` with body `{"signatures": [<journey signature>...]}`
answers `journey_times[]` in request order (`time`, `time_mode`, `leg_times[]`, `formatted_price`,
`traffic_level`, `request_signature`). The page polls it every 30 s up to 10 times.

Place names come from two `POST /api/4/searchpost` calls (one per endpoint name) on a cold load.

## Journey detail and sharing

Clicking a selected journey navigates to `/trip/signature?signature=<journey signature,
pako-deflated, base64>` and fetches the same URL with `&meta_only=true` for head tags. In-app
navigation reuses the stored journey; a cold load posts `/api/1/refreshjourneys` with
`{signatures, time_mode: SIGNATURE_EXACT|SIGNATURE, region_id, status_format: "html"}` (INFERENCE).
The detail header has send-to-phone (saves the journey to the account,
`POST /api/1/identity/documents/SavedJourney`) and share (`GET /api/1/createtripurl`, which creates a
public link). Neither was pressed. `/trip/{slug}` resolves a shared link with `gettrip`.

## Place search

`POST /api/4/searchpost`, `Content-Type: application/x-www-form-urlencoded; charset=UTF-8` with a
JSON body `{"query", "region_id", "is_refinement", "refinement_data": {"is_chain": true},
"powersearch": false}` (optional `location` bias, `search_providers`, `partner`), headers
`Citymapper-Client: Web Search` and `Citymapper-Region: <region_id>`. Results interleave headings
(`result_type: heading`, for example Stations and Results) and items: Citymapper stations (`type
station`, `brands`, `lines`, `coords`) and Google places (`address`, `coords`,
`place_details_available`). Google results observed carry coordinates, so `placeresolve` was not
needed. A map click on a Google POI named the point without `/geocode`.

## Nearby

City page tiles link to `/{region}/{mode_slug}/{stop_type}?name=&coords=lat,lng`, for example
`/nyc/subway/stations`, `/nyc/bus/stops`, `/nyc/bike/docks`, `/nyc/rail/stations`,
`/nyc/ferry/piers`, `/paris/metro/stations`. Request: `GET /api/3/nearby?brand_ids=<from
nearby_modes.request_brand_ids>&location=lat,lng&region_id=&mode_id=&limit=50&extended=1`.
Response `elements[]` (id, name, coords, kind `transitstop` or `cycledock`, alias, brand_ids,
route_ids, route_names, bearing, `walk_time_seconds`); docks add `cycles_available`,
`cycles_spaces`, `cycles_broken`, `cycles_total`, `cycles_electric_available`,
`cycles_manual_available`, `has_low_vehicles`. Plus `bounding_box` and `last_updated_time`. NYC
subway answered 30 elements for limit 50.

## Stops and live departures

Stop pages are `/{region}/{mode_slug}/{stop_type}/{alias}` (aliases from nearby, for example
`times-sq-42-st`, `7-avw-44-st`, `grand-central`, `midtown-w-39th-st`, `chatelet`). Bike docks have no
page (404).

1. `GET /api/3/stopinfo?ids=<alias or id>&region_id=` returns `stops[]` (id, alias, name, coords,
   route_ids, brand_ids, exits, `sharing_urls[].departure_api`) and `routes[]`.
2. The departures endpoint depends on the brand:

| Stop type | Endpoint | Shape |
|---|---|---|
| Bus, ferry | `GET /api/1/departures?headways=1&ids=<id>&region_id=` | `stops[].services[]` with `route_id`, `headsign`, `live_departures_seconds[]` |
| Metro (NYC subway, Paris metro) | `GET /api/2/metrodepartures?headways=1&ids=<id>&region_id=` | `stations[].sections[].departure_groupings[].departures[]` with `route_id`, `destination_name`, `time_seconds` (live) or `scheduled_time` (ISO), `is_advisory_message` |
| Commuter rail (MNR) | `GET /api/1/raildepartures?headways=1&ids=<id>&region_id=` | `stations[].departures[]` with `scheduled_time`, `expected_departure_time`, `time_seconds`, `is_live`, `platform_number`, `stops[]` |

3. `GET /api/2/nearby?brand_ids=&location=&limit=50&region_id=` (jQuery, `x-requested-with`) for
   nearby stops on the page.

The page re-polls departures every 30 s. Times are relative seconds or absolute ISO times, so the
program's checks are on types and order, never values.

## Lines and line search

- City page "Find a bus or line": `GET /api/2/findtransport?query=M15&region_id=us-nyc` per
  keystroke (observed by URL; body not captured). Picking a result opens the line page.
- Line page `/{region}/{mode_slug}/{line_alias}` (for example `/nyc/subway/subway-6`,
  `/nyc/bus/new-york-city-bus-m15`; `/{region}/l/{alias}` redirects there):
  `GET /api/1/routeinfo?route=<alias>&region_id=&weekend=1&status_format=rich&extended=1` returns
  `routes[]` (name, long_name, brand, mode, colors, `live_line_code`, `live_availability`, url,
  aliases, `status`, `patterns[]` with `stop_points` and `path`) and a `stops` map keyed by stop id.
- Lines card and strike map: `GET /api/2/routeinfo?route_ids=1,2,...&region_id=&weekend=1&status_format=rich`
  (NYC: 34 ids, 444 KB).
- `vehiclelocations` is called by the line page only when the line has live vehicles; none of the
  three lines walked did.

## Status and disruptions

`GET /api/1/routestatus?region_id=&format=rich` with `Citymapper-Region`. `groupings[]` by mode (NYC: 8
groupings, Subway 29 routes, LIRR 12, MNR 6, ferry 5, NJ Transit rail 8, light rail 2, PATH 5,
partners 0 routes). Each route's `status` has `level` (0 good, 1 minor, 2 severe as observed), `summary`,
`description`, `replacements`, and `disruptions[]` with `level`, `summary`, a `description` template
whose `{0}`, `{1}` placeholders map to `replacements` (route icons or bold text), and affected
`stops`. Refetched every 2 minutes by the page.

## City coverage

`/cities` makes no API call; the city list is `window.citymapper.regions` and `citiesInRegions` in the
HTML. The home page fetches `GET /resource/region-info/{region_id}` (JSON region config) and
`GET /resource/brand-directory` (445 KB brand catalogue).

## Account features (not exercised)

See [risks-and-open-questions.md](../knowledge/risks-and-open-questions.md#account) for the list of
identity endpoints and why none was called.
