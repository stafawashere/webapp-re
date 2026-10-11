---
id: eta
goal: Read a shared ETA
method: POST
url: https://citymapper.com/api/1/eta?region_id={region_id}
surface: rest
operation: 
operation_id: 
status: dead
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 
verify_count: 0
fail_count: 2
runs: [run-2026-10-10-082844, run-2026-10-10-090401]
---

## Goal

Read a shared ETA

## Request

```
POST https://citymapper.com/api/1/eta?region_id={region_id}
```

## Headers that matter

Names in front matter. Where each value comes from: fill in.

## Cookies that gate it

unknown

## Request body

signature

## Response, trimmed

{}

## Success signal

unknown

## Failure signals

unknown

## Notes

read from the bundle only, not observed live.

## Replay template

```json
{
   "method": "POST",
   "url": "https://citymapper.com/api/1/eta?region_id={region_id}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 fail: replay eta-1: HTTP 404, 404 'Page Not Found' HTML for fresh signatures in New York and Paris
- 2026-10-10 run-2026-10-10-090401 fail: replay eta-2: HTTP 404, 404 'Page Not Found' HTML for fresh signatures in New York and Paris

### 2026-10-10 run-2026-10-10-090401

Retired upstream: two replays on 2026-10-10 in two regions answered 404 (see Verification history). Command kept and reported as blocked.
