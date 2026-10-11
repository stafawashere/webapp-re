---
id: createtripurl
goal: Create a share link for a journey
method: GET
url: https://citymapper.com/api/1/createtripurl?signature={signature}&trip_region_id={region_id}
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

Create a share link for a journey

## Request

```
GET https://citymapper.com/api/1/createtripurl?signature={signature}&trip_region_id={region_id}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"url": "str"}

## Success signal

unknown

## Failure signals

unknown

## Notes

read from the bundle only, not observed live. Write despite GET: creates a public short link.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/1/createtripurl?signature={signature}&trip_region_id={region_id}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
