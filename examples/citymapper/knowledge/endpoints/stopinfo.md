---
id: stopinfo
goal: Get a stop or station's details
method: GET
url: https://citymapper.com/api/3/stopinfo?ids={alias or id}&region_id={region_id}
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 13
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401, run-2026-10-10-113603]
---

## Goal

Get a stop or station's details

## Request

```
GET https://citymapper.com/api/3/stopinfo?ids={alias or id}&region_id={region_id}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"stops[]": "id, requested_id, alias, name, coords, route_ids, brand_ids, url, sharing_urls[{departure_api, url}], exits[], stop_curation_url_ids", "routes[]": "id, name, brand_id, icon_name, color"}

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
   "url": "https://citymapper.com/api/3/stopinfo?ids={alias or id}&region_id={region_id}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay stopinfo-1: HTTP 200, 1 stops items
- 2026-10-10 run-2026-10-10-090401 pass: replay stopinfo-2: HTTP 200, 1 stops items
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-stop (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-departures-metro (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-departures-bus (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-departures-rail (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-departures-metro (verify-2026-10-10-092313.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-departures-bus (verify-2026-10-10-092313.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-departures-rail (verify-2026-10-10-092313.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-stop (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-departures-metro (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-departures-bus (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-departures-rail (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 2 requests
