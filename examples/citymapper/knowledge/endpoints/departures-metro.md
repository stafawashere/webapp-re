---
id: departures-metro
goal: Get live departures at a stop or station
method: GET
url: https://citymapper.com/api/2/metrodepartures?headways=1&ids={station_id}&region_id={region_id}
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 2
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401]
---

## Goal

Get live departures at a stop or station

## Request

```
GET https://citymapper.com/api/2/metrodepartures?headways=1&ids={station_id}&region_id={region_id}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"stations[]": "station{name, coords, live_code, status}, sections[{id, name, departure_types, departure_groupings[{grouping_id, departures[{route_id, destination_name, time_seconds | scheduled_time, pattern_id, direction_id, is_advisory_message}]}]}], routes[], messages[]", "last_updated_time": "str"}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk. Observed in NYC and Paris.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/2/metrodepartures?headways=1&ids={station_id}&region_id={region_id}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay metro-1: HTTP 200, 1 stations items
- 2026-10-10 run-2026-10-10-090401 pass: replay metro-2: HTTP 200, 1 stations items
