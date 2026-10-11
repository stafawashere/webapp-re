---
id: trip-meta
goal: Open a journey's detail
method: GET
url: https://citymapper.com/trip/signature?signature={deflated base64}&meta_only=true
surface: html
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 2
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401]
---

## Goal

Open a journey's detail

## Request

```
GET https://citymapper.com/trip/signature?signature={deflated base64}&meta_only=true
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

observed live in the 2026-10-10 scope walk. Head-tag refresh on client navigation (hackyReplacePageMeta). The signature param is the journey signature, pako-deflated and base64 encoded.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/trip/signature?signature={deflated base64}&meta_only=true",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay trip-meta-2: HTTP 200, marker found
- 2026-10-10 run-2026-10-10-090401 pass: replay trip-meta-3: HTTP 200, marker found
