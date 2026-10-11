---
id: routeinfo1
goal: Get a line's branches, stops, path and status
method: GET
url: https://citymapper.com/api/1/routeinfo?route={alias}&region_id={region_id}&weekend=1&status_format=rich&extended=1
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

Get a line's branches, stops, path and status

## Request

```
GET https://citymapper.com/api/1/routeinfo?route={alias}&region_id={region_id}&weekend=1&status_format=rich&extended=1
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"routes[]": "id, name, long_name, brand, mode, color, live_line_code, live_availability, url, aliases, status{level, summary, description, replacements}, patterns[{id, name, pattern_type, path, stop_points}]", "stops": "{stop_id: {name, coords, routes, brands, live_code, status}}", "feeds[]": "...", "status": "int"}

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
   "url": "https://citymapper.com/api/1/routeinfo?route={alias}&region_id={region_id}&weekend=1&status_format=rich&extended=1",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay routeinfo1-1: HTTP 200, 1 routes items
- 2026-10-10 run-2026-10-10-090401 pass: replay routeinfo1-2: HTTP 200, 1 routes items
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-line (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-line (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
