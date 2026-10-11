---
id: walk7
goal: Plan a walking route
method: GET
url: https://citymapper.com/api/7/walk
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

Plan a walking route

## Request

```
GET https://citymapper.com/api/7/walk
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"journeys[]": "duration_seconds, distance_meters, calories, legs[], signature, profile_id, profile_localized_name", "shared.station_exits[]": "..."}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk. limit=2 in the UI.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/7/walk",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay walk7-1: HTTP 200, 2 journeys items
- 2026-10-10 run-2026-10-10-090401 pass: replay walk7-2: HTTP 200, 2 journeys items
- 2026-10-10 run-2026-10-10-090401 pass: program live check plan-walk (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check plan-walk (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
