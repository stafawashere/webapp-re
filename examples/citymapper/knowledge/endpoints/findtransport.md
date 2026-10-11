---
id: findtransport
goal: Find a bus or line by name or number
method: GET
url: https://citymapper.com/api/2/findtransport?query={text}&region_id={region_id}
surface: rest
operation: 
operation_id: 
status: verified
required_headers: [accept, content-type, referer]
required_cookies: []
first_seen: 2026-10-10
last_seen: 2026-10-10
last_verified: 2026-10-10
verify_count: 5
fail_count: 0
runs: [run-2026-10-10-082844, run-2026-10-10-090401, run-2026-10-10-113603]
---

## Goal

Find a bus or line by name or number

## Request

```
GET https://citymapper.com/api/2/findtransport?query={text}&region_id={region_id}
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

observed live in the 2026-10-10 scope walk. Observed in your browser (URL only, body not captured).

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/2/findtransport?query={text}&region_id={region_id}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay findtransport-1: HTTP 200, keys results
- 2026-10-10 run-2026-10-10-090401 pass: replay findtransport-2: HTTP 200, keys results
- 2026-10-10 run-2026-10-10-090401 pass: replay findtransport-3: HTTP 200, 15 route results
- 2026-10-10 run-2026-10-10-090401 pass: program live check find-line (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 1 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check find-line (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 1 requests
