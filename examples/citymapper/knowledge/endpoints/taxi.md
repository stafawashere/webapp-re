---
id: taxi
goal: Estimate a cab or on-demand ride
method: GET
url: https://citymapper.com/api/2/taxi
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

Estimate a cab or on-demand ride

## Request

```
GET https://citymapper.com/api/2/taxi
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"routes[]": "mode taxi, length_meters, duration_seconds, legs[]", "on_demand_model": "title, categories[]", "status": "int"}

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
   "url": "https://citymapper.com/api/2/taxi",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay taxi-1: HTTP 200, keys present
- 2026-10-10 run-2026-10-10-090401 pass: replay taxi-2: HTTP 200, keys present
- 2026-10-10 run-2026-10-10-090401 pass: program live check plan-cab (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check plan-cab (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
