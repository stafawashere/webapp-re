---
id: identity-favorites-create
goal: Favourite or unfavourite a stop or station
method: POST
url: https://citymapper.com/api/1/identity/favorites
surface: rest
operation: 
operation_id: 
status: hypothesis
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 
verify_count: 0
fail_count: 0
runs: [run-2026-10-10-082844]
---

## Goal

Favourite or unfavourite a stop or station

## Request

```
POST https://citymapper.com/api/1/identity/favorites
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

target_type, target_id, region_id

## Response, trimmed

{}

## Success signal

unknown

## Failure signals

unknown

## Notes

read from the bundle only, not observed live. target_type 1 bus stop, 2 station, 3 transit line (bundle).

## Replay template

```json
{
   "method": "POST",
   "url": "https://citymapper.com/api/1/identity/favorites",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
