---
id: cities-html
goal: List every supported city and region
method: GET
url: https://citymapper.com/cities
surface: html
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

List every supported city and region

## Request

```
GET https://citymapper.com/cities
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

observed live in the 2026-10-10 scope walk. Same window.citymapper globals; city tiles link to /{region_slug}.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/cities",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay cities-html-1: HTTP 200, marker found
- 2026-10-10 run-2026-10-10-090401 pass: replay cities-html-2: HTTP 200, marker found
- 2026-10-10 run-2026-10-10-090401 pass: program live check list-cities (verify-2026-10-10-091208.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check list-cities (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
