---
id: vehiclehire
goal: Plan with scooters or hire vehicles
method: GET
url: https://citymapper.com/api/7/vehiclehire
surface: rest
operation: 
operation_id: 
status: dead
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 
verify_count: 0
fail_count: 2
runs: [run-2026-10-10-082844, run-2026-10-10-090401]
---

## Goal

Plan with scooters or hire vehicles

## Request

```
GET https://citymapper.com/api/7/vehiclehire
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

read from the bundle only, not observed live. Bundle only, no caller.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/7/vehiclehire",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 fail: replay vehiclehire-1: HTTP 404, 404 {"error": "This API is no longer supported"} in London and Paris
- 2026-10-10 run-2026-10-10-090401 fail: replay vehiclehire-2: HTTP 404, 404 {"error": "This API is no longer supported"} in London and Paris

### 2026-10-10 run-2026-10-10-090401

Retired upstream: two replays on 2026-10-10 in two regions answered 404 (see Verification history). Command kept and reported as blocked.
