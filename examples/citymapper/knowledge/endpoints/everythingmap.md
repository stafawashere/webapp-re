---
id: everythingmap
goal: Get everything on the map around a point
method: GET
url: https://citymapper.com/api/1/everythingmap?location={lat,lng}&size={size}&region_id={region_id}
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

Get everything on the map around a point

## Request

```
GET https://citymapper.com/api/1/everythingmap?location={lat,lng}&size={size}&region_id={region_id}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{}

## Success signal

unknown

## Failure signals

unknown

## Notes

read from the bundle only, not observed live.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/1/everythingmap?location={lat,lng}&size={size}&region_id={region_id}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay everything-2: HTTP 200, object
- 2026-10-10 run-2026-10-10-090401 pass: replay everything-3: HTTP 200, object
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-map-around (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-map-around (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
