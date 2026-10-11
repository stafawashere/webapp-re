---
id: schedules
goal: Get a stop's timetable
method: GET
url: https://citymapper.com/api/1/schedules?id={stop_id}&region_id={region_id}&time={time}
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

Get a stop's timetable

## Request

```
GET https://citymapper.com/api/1/schedules?id={stop_id}&region_id={region_id}&time={time}
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

read from the bundle only, not observed live.

## Replay template

```json
{
   "method": "GET",
   "url": "https://citymapper.com/api/1/schedules?id={stop_id}&region_id={region_id}&time={time}",
   "headers": [
      "accept",
      "content-type",
      "referer"
   ],
   "body": null
}
```

## Verification history
- 2026-10-10 run-2026-10-10-090401 pass: replay schedules-1: HTTP 200, keys id,services,departures,labels,next_time
- 2026-10-10 run-2026-10-10-090401 pass: replay schedules-2: HTTP 200, keys present
- 2026-10-10 run-2026-10-10-090401 pass: program live check get-stop-schedule (verify-2026-10-10-090820.json): exit 0, schema and invariants passed, 2 requests
- 2026-10-10 run-2026-10-10-113603 pass: program live check get-stop-schedule (verify-2026-10-10-113605.json): exit 0, schema and invariants passed, 2 requests
