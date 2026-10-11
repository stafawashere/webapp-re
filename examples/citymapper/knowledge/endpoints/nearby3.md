---
id: nearby3
goal: List nearby stops, stations, piers or bike docks for one mode
method: GET
url: https://citymapper.com/api/3/nearby
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 7
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401, run-2026-10-10-113603]
---

## Goal

List nearby stops, stations, piers or bike docks for one mode

## Request

```
GET https://citymapper.com/api/3/nearby
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"elements[]": "id, name, coords, kind (transitstop, cycledock, ...), brand_ids, route_ids, route_names, route_icon_names, alias, bearing, walk_time_seconds; docks add cycles_available, cycles_spaces, cycles_total, cycles_electric_available, cycles_manual_available", "bounding_box": "southwest_corner_coords, northeast_corner_coords", "last_updated_time": "str"}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk. brand_ids and mode_id come from the region's nearby_modes.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/3/nearby",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay nearby3-1: HTTP 200, 50 elements items
- 2026-10-10 run-2026-10-10-090401 pass: replay nearby3-2: HTTP 200, 20 elements items
- 2026-10-10 run-2026-10-10-090401 pass: program live check find-nearby (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check find-nearby-london-bus (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check find-nearby-london-bus (verify-2026-10-10-092313.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check find-nearby (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check find-nearby-london-bus (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
