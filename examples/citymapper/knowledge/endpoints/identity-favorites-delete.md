---
id: identity-favorites-delete
goal: Favourite or unfavourite a stop or station
method: DELETE
url: https://citymapper.com/api/1/identity/favorites/{favourite_id}
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
DELETE https://citymapper.com/api/1/identity/favorites/{favourite_id}
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
   "method": "DELETE",
   "url": "https://citymapper.com/api/1/identity/favorites/{favourite_id}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
