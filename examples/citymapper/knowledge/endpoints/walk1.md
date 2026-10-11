---
id: walk1
goal: Plan a walking route
method: GET
url: https://citymapper.com/api/1/walk
surface: rest
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

Plan a walking route

## Request

```
GET https://citymapper.com/api/1/walk
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

read from the bundle only, not observed live. Older walk endpoint; bundle only.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/1/walk",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay walk1-2: HTTP 200, 1 routes items
- 2026-10-10 run-2026-10-10-090401 pass: replay walk1-3: HTTP 200, 1 routes items
