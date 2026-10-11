---
id: journeytimes
goal: Refresh live times of planned journeys
method: POST
url: https://citymapper.com/api/1/journeytimes?region_id={region_id}
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, origin, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 4
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401, run-2026-10-10-113603]
---

## Goal

Refresh live times of planned journeys

## Request

```
POST https://citymapper.com/api/1/journeytimes?region_id={region_id}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

signatures, partner

## Response, trimmed

{"journey_times[]": "time (ISO with offset), time_mode (NOWISH, ...), formatted_price, leg_times[], request_signature, traffic_level"}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk. Body {signatures: [<journey signature JSON string>]}; response order follows the request.

## Replay template

```json
{
   "method": "POST",
   "url": "https://citymapper.com/api/1/journeytimes?region_id={region_id}",
   "headers": [
      "accept",
      "content-type",
      "origin",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay journeytimes-1: HTTP 200, 3 journey_times items
- 2026-10-10 run-2026-10-10-090401 pass: replay journeytimes-2: HTTP 200, 2 journey_times items
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-journey-times (verify-2026-10-10-091208.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-journey-times (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
