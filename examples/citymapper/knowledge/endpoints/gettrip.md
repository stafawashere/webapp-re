---
id: gettrip
goal: Open a shared trip link
method: GET
url: https://citymapper.com/api/1/gettrip?slug={slug}
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

Open a shared trip link

## Request

```
GET https://citymapper.com/api/1/gettrip?slug={slug}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

none

## Response, trimmed

{"signature": "str"}

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
   "url": "https://citymapper.com/api/1/gettrip?slug={slug}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
