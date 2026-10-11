---
id: refreshjourneys
goal: Open a journey's detail
method: POST
url: https://citymapper.com/api/1/refreshjourneys?region_id={region_id}
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

Open a journey's detail

## Request

```
POST https://citymapper.com/api/1/refreshjourneys?region_id={region_id}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

signatures, time_mode, region_id, partner, use_departures, status_format

## Response, trimmed

{"refreshed_journeys[]": "journey, error", "shared": "..."}

## Success signal

unknown

## Failure signals

unknown

## Notes

read from the bundle only, not observed live. time_mode SIGNATURE_EXACT or SIGNATURE; bundle and route table, not fired by in-app navigation.

## Replay template

```json
{
   "method": "POST",
   "url": "https://citymapper.com/api/1/refreshjourneys?region_id={region_id}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay refresh-1: HTTP 200, 1 refreshed_journeys items
- 2026-10-10 run-2026-10-10-090401 pass: replay refresh-2: HTTP 200, 1 refreshed_journeys items
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-journey (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-journey (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
