---
id: cycle
goal: Plan a cycling route (own bike or bike share)
method: GET
url: https://citymapper.com/api/6/cycle
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 4
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401, run-2026-10-10-113603]
---

## Goal

Plan a cycling route (own bike or bike share)

## Request

```
GET https://citymapper.com/api/6/cycle
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"journeys[]": "journey_kind (cycle_personal, cycle_hire), profile_id, journey_profile, duration_seconds, distance_meters, legs[], signature, formatted_price, representative_brand_id", "shared.cycle_docks[]": "dock ids and availability"}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/6/cycle",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay cycle-1: HTTP 200, 6 journeys items
- 2026-10-10 run-2026-10-10-090401 pass: replay cycle-2: HTTP 200, 6 journeys items
- 2026-10-10 run-2026-10-10-090401 pass: program live check plan-cycle (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check plan-cycle (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
