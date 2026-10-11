---
id: geocode
goal: Name a point clicked on the map
method: GET
url: https://citymapper.com/geocode?lat={lat}&lng={lng}
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

Name a point clicked on the map

## Request

```
GET https://citymapper.com/geocode?lat={lat}&lng={lng}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"results[]": "address_components[], formatted_address (Google geocoder shape)"}

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
   "url": "https://citymapper.com/geocode?lat={lat}&lng={lng}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay geocode-1: HTTP 200, 16 results items
- 2026-10-10 run-2026-10-10-090401 pass: replay geocode-2: HTTP 200, 16 results items
- 2026-10-10 run-2026-10-10-090401 pass: program live check reverse-geocode (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check reverse-geocode (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
