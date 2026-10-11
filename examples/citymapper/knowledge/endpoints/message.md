---
id: message
goal: Read the site-wide service message
method: GET
url: https://citymapper.com/api/2/message?had_previous_versions=0
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

Read the site-wide service message

## Request

```
GET https://citymapper.com/api/2/message?had_previous_versions=0
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

accept, citymapper-region, content-type, referer

## Response, trimmed

{"messages[]": "..."}

## Success signal

unknown

## Failure signals

unknown

## Notes

observed live in the 2026-10-10 scope walk.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/2/message?had_previous_versions=0",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay message-1: HTTP 200, keys present
- 2026-10-10 run-2026-10-10-090401 pass: replay message-2: HTTP 200, keys present
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-service-message (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-service-message (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
