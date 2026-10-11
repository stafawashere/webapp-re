---
id: resource-brand-directory
goal: List transport brands (operators) worldwide
method: GET
url: https://citymapper.com/resource/brand-directory
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

List transport brands (operators) worldwide

## Request

```
GET https://citymapper.com/resource/brand-directory
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

observed live in the 2026-10-10 scope walk. 445 KB JSON brand catalogue.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/resource/brand-directory",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay brand-directory-1: HTTP 200, type dict
- 2026-10-10 run-2026-10-10-090401 pass: replay brand-directory-2: HTTP 200, 2051 brands items
- 2026-10-10 run-2026-10-10-090401 pass: program live check list-brands (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check list-brands (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
