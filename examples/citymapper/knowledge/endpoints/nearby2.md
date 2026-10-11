---
id: nearby2
goal: List nearby stops, stations, piers or bike docks for one mode
method: GET
url: https://citymapper.com/api/2/nearby
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

List nearby stops, stations, piers or bike docks for one mode

## Request

```
GET https://citymapper.com/api/2/nearby
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

accept, referer, x-requested-with

## Response, trimmed

{"elements[]": "same element shape as nearby3", "bounding_box": "..."}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk. jQuery call on stop pages.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/2/nearby",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay nearby2-1: HTTP 200, 50 elements items
- 2026-10-10 run-2026-10-10-090401 pass: replay nearby2-3: HTTP 200, 20 elements items
