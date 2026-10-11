---
id: identity-places-update
goal: Edit a saved place
method: PUT
url: https://citymapper.com/api/1/identity/places/{place_id}
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

Edit a saved place

## Request

```
PUT https://citymapper.com/api/1/identity/places/{place_id}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

name, address, coords, role

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
   "method": "PUT",
   "url": "https://citymapper.com/api/1/identity/places/{place_id}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
