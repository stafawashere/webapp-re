---
id: identity-places-create
goal: Save a place
method: POST
url: https://citymapper.com/api/1/identity/places
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

Save a place

## Request

```
POST https://citymapper.com/api/1/identity/places
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

name, address, coords, role, place_id

## Response, trimmed

{}

## Success signal

unknown

## Failure signals

unknown

## Notes

read from the bundle only, not observed live. Body is the place object; role home or work for those slots (bundle).

## Replay template

```json
{
   "method": "POST",
   "url": "https://citymapper.com/api/1/identity/places",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
