---
id: identity-user-data
goal: Read the signed-in user
method: GET
url: https://citymapper.com/api/1/identity/user_data
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

Read the signed-in user

## Request

```
GET https://citymapper.com/api/1/identity/user_data
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

observed live in the 2026-10-10 scope walk. 403 with an empty body while signed out (observed); user object when signed in.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/1/identity/user_data",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay user-data-1: HTTP 403, signed-out 403
- 2026-10-10 run-2026-10-10-090401 pass: replay user-data-2: HTTP 403, signed-out 403
- 2026-10-10 run-2026-10-10-090401 pass: program live check whoami (verify-2026-10-10-091208.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check whoami (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
