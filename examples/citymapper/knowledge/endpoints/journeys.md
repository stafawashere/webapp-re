---
id: journeys
goal: Plan a transit journey
method: GET
url: https://citymapper.com/api/7/journeys
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 8
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401, run-2026-10-10-113603]
---

## Goal

Plan a transit journey

## Request

```
GET https://citymapper.com/api/7/journeys
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"sections[]": "id, name, journeys[] (indexes), ad_may_follow", "journeys[]": "start, end, legs[], duration_seconds, walk_seconds, distance_meters, calories, signature, journey_equivalence_hash, formatted_price, price_amount, currency_code, step_free, trip_curation_url_ids, log", "journeys[].legs[]": "mode (walk, transit, cycle, ...), routes[], stops[] (id, name, coords, duration_seconds_to_here), shape[[lat,lng]], frequency, departure_time, arrival_time, pattern_ids, boarding_info", "shared": "station_exits[], trip_curation_urls[]", "routing_request_id": "str"}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk. Transit journeys. start and end are 'lat,lng'. Observed keys: start, end, sname, ename, saddr, region_id, include_stepfree=1, include_via_microtransit=1, status_format=html, arrival_time or departure_time ISO UTC. 97 KB for NYC, 166 KB for London.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/7/journeys",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay journeys-1: HTTP 200, 11 journeys items
- 2026-10-10 run-2026-10-10-090401 pass: replay journeys-2: HTTP 200, 19 journeys items
- 2026-10-10 run-2026-10-10-090401 pass: replay journeys-3: HTTP 200, 12 journeys items
- 2026-10-10 run-2026-10-10-090401 pass: program live check plan-journey-nyc (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check plan-journey-london (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-090401 pass: program live check plan-journey-nyc (verify-2026-10-10-091208.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check plan-journey-nyc (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check plan-journey-london (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 2 requests
