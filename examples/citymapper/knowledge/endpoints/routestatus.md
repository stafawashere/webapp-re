---
id: routestatus
goal: Get the status of every line in a city
method: GET
url: https://citymapper.com/api/1/routestatus?region_id={region_id}&format=rich
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 6
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401, run-2026-10-10-113603]
---

## Goal

Get the status of every line in a city

## Request

```
GET https://citymapper.com/api/1/routestatus?region_id={region_id}&format=rich
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

accept, citymapper-region, content-type, referer

## Response, trimmed

{"groupings[]": "id, name, include_in_disruption_count, routes[{name, long_name, brand, aliases, status{level, summary, description, replacements, disruptions[{level, summary, description, replacements, stops}]}}], partners[]", "last_updated_time": "str", "referenced_routes[]": "..."}

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
   "url": "https://citymapper.com/api/1/routestatus?region_id={region_id}&format=rich",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay routestatus-1: HTTP 200, 8 groupings items
- 2026-10-10 run-2026-10-10-090401 pass: replay routestatus-2: HTTP 200, 7 groupings items
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-line-status (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-disruptions (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-line-status (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-disruptions (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
