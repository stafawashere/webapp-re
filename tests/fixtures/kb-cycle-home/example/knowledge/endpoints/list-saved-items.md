---
id: list-saved-items
goal: list my saved items
method: GET
url: https://app.example.test/api/saved-items
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [x-csrf-token]
required_cookies: [sid]
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 1
fail_count: 0
runs: [run-2026-10-10-173440]
---

## Goal

list my saved items

## Request

```
GET https://app.example.test/api/saved-items
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

sid

## Request body

Field names and value shapes, no values.

## Response, trimmed

Paste shape.py output trimmed to what answers the goal.

## Success signal

unknown

## Failure signals

unknown

## Notes



## Replay template

```json
{
   "method": "GET",
   "url": "https://app.example.test/api/saved-items",
   "headers": [
      "x-csrf-token"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-173440 pass: 200, 7 items
