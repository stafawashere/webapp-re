---
id: routeinfo2
goal: Get several lines at once
method: GET
url: https://citymapper.com/api/2/routeinfo?route_ids={id,id}&region_id={region_id}&weekend=1&status_format=rich
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

Get several lines at once

## Request

```
GET https://citymapper.com/api/2/routeinfo?route_ids={id,id}&region_id={region_id}&weekend=1&status_format=rich
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"routes[]": "same route shape as routeinfo1", "stops": "{stop_id: {...}}"}

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
   "url": "https://citymapper.com/api/2/routeinfo?route_ids={id,id}&region_id={region_id}&weekend=1&status_format=rich",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay routeinfo2-1: HTTP 200, 5 routes items
- 2026-10-10 run-2026-10-10-090401 pass: replay routeinfo2-2: HTTP 200, 2 routes items
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-lines (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-lines (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
